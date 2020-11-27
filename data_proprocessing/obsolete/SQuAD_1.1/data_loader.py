import os
import math
import random
import sys
import json
import time


sys.path.append('..')

from base.data_loader import BaseDataLoader
from base.globals import *
from base.partition import *


data_dir shoule be '../../../../data/fednlp/span_extraction/SQuAD_1_1.1'


class DataLoader(BaseDataLoader):
    def __init__(self, data_path, partition, **kwargs):
        super().__init__(data_path, partition, **kwargs)
        allowed_keys = {"document_padding", "question_padding", "tokenized", "source_max_sequence_length",
                        "target_max_sequence_length", "vocab_path", "initialize"}
        self.__dict__.update((key, False) for key in allowed_keys)
        self.__dict__.update((key, value) for key, value in kwargs.items() if key in allowed_keys)
        self.source_sequence_length = []
        self.question_sequence_length = []
        self.document_X = []
        self.question_X = []
        self.answer_X = []
        self.attributes = dict()
        self.attributes['inputs'] = []

        if self.tokenized:
            self.vocab = dict()
            self.qas_vocab = dict()
            if self.initialize:
                self.vocab[SOS_TOKEN] = len(self.vocab)
                self.vocab[EOS_TOKEN] = len(self.vocab)
        if self.document_padding or self.question_padding:
            self.vocab[PAD_TOKEN] = len(self.vocab)
            self.qas_vocab[PAD_TOKEN] = len(self.vocab)
    def tokenize(self,document):
        # Create a blank Tokenizer with just the English vocab
        tokens = [str(token) for token in spacy_tokenizer.en_tokenizer(document)]
        return tokens
    def process_attributes(self):
        self.attributes['n_clients'] = len(self.attributes['inputs'])

    def process_data(self,client_idx=None):
        with open(self.data_path,"r",encoding='utf-8') as f:
            data = json.load(f)
            max_document_length = -math.inf
            max_question_length = -math.inf

            for index, document in enumerate(data["data"]):
                if client_idx is not None and client_idx != self.attributes["inputs"][cnt]:
                    cnt+=1
                    continue
                self.attributes['inputs'].append(index)
                single_document = "".join([paragraph["context"] for paragraph in document["paragraphs"]])

                if self.tokenized:
                    document_tokens = self.tokenize(single_document)
                    self.document_X.append(document_tokens)
                    self.source_sequence_length.append(len(document_tokens))
                    max_document_length = max(max_document_length,len(document_tokens))
                    for i in document_tokens:
                        if i not in self.vocab:
                            self.vocab[i] = len(self.vocab)
                else:
                    self.document_X.append([single_document])


                for paragraph in document["paragraphs"]:
                    single_doc_question = []
                    single_doc_answers = []
                    single_doc_question_length = []


                    for qas in paragraph["qas"]:
                        question = qas["question"]
                        if self.tokenized:
                            question = self.tokenize(question)
                            single_doc_question.append(question)
                            max_question_length = max(max_question_length,len(question))
                            for i in question:
                                if i not in self.qas_vocab:
                                    self.qas_vocab[i] = len(self.qas_vocab)
                        else:
                            single_doc_question.append([question])
                            max_question_length =  max(max_question_length,len(question))


                        answer  = []
                        for answers in qas["answers"]:
                            if(answers["text"] not in answer):
                                answer.append(answers["text"])
                                single_doc_question_length.append(len(question))
                                start = answers["answer_start"]
                                end = start + len(answers["text"].rstrip())
                                single_doc_answers.append([start,end])

                self.Y.append(single_doc_answers)
                self.question_X.append(single_doc_question)
                self.question_sequence_length.append(single_doc_question_length)

        return max_document_length, max_question_length


    def data_loader(self,client_idx=None):
        result = dict()

        if client_idx is not None:
            max_document_length , max_question_length = self.process_data(client_idx)
        else:
            max_document_length , max_question_length = self.process_data()

        if self.document_padding:
            self.padding_data(self.document_X, max_document_length,self.initialize)
        if self.question_padding:
            self.padding_data(self.question_X, max_question_length,self.initialize)

        if callable(self.partition):
            self.attributes = self.partition(self.document_X, self.Y)
        else:
            self.process_attributes()

        if self.tokenized:
            result['vocab'] = self.vocab
            result['question_vocab'] = self.qas_vocab

        result['document_X'] = self.document_X
        result['question_X'] = self.question_X
        result['Y'] = self.Y
        result['attributes'] = self.attributes
        result['source_sequence_length'] = self.source_sequence_length
        result['question_sequence_length'] = self.question_sequence_length
        result['document_max_sequence_length'] = max_document_length
        result['question_max_sequence_length'] = max_question_length

        return result

