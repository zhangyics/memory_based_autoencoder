import os
import json
import time
import codecs
import tensorflow as tf
import data
import shutil
from  result_evaluate import Evaluate
import util
import nltk
from nltk.translate.bleu_score import corpus_bleu
from nltk.translate.bleu_score import corpus_bleu
import batcher_classification as bc
FLAGS = tf.app.flags.FLAGS

class Generated_sample(object):
    def __init__(self, model, vocab, batcher, sess):
        self._model = model
        self._vocab = vocab
        self._sess = sess

        self.batches = batcher.get_batches(mode='train')
        self.valid_batches = batcher.get_batches(mode='valid')
        self.valid_transfer = batcher.get_batches(mode='valid-transfer')
        self.test_transfer = batcher.get_batches(mode='test-transfer')
        self.current_batch = 0

        self.valid_sample_whole_positive_dir = "valid-generated"
        self.valid_sample_whole_negative_dir = "valid-generated-transfer"
        self.test_sample_whole_negative_dir = "test-generated-transfer"

        if not os.path.exists(self.valid_sample_whole_positive_dir): os.mkdir(self.valid_sample_whole_positive_dir)
        if not os.path.exists(self.valid_sample_whole_negative_dir): os.mkdir(self.valid_sample_whole_negative_dir)
        if not os.path.exists(self.test_sample_whole_negative_dir): os.mkdir(self.test_sample_whole_negative_dir)

    def write_negtive_to_json(self, positive, negetive, score, counter, dir):

        positive_file = os.path.join(dir, "%06d.txt" % (counter // 1000))
        #negetive_file = os.path.join(negtive_dir, "%06d.txt" % (counter // 1000))
        write_positive_file = codecs.open(positive_file, "a", "utf-8")
        #write_negetive_file = codecs.open(negetive_file, "a", "utf-8")
        dict = {"example": str(positive),
                "generated": str(negetive),
                "target_score" : score,
                }
        string_ = json.dumps(dict)
        write_positive_file.write(string_ + "\n")
        write_positive_file.close()

    def generator_validation_negative_example(self, path, batcher, model_class,sess_cls, cla_batcher, mode):

        if not os.path.exists(path): os.mkdir(path)
        shutil.rmtree(path)
        if not os.path.exists(path): os.mkdir(path)
        counter = 0
        step = 0

        t0 = time.time()
        if mode == 'valid-transfer':
            batches = self.valid_transfer
        elif mode == 'test-transfer':
            batches = self.test_transfer
            print("len test", len(batches))

        list_ref =[]
        list_pre = []
        right = 0
        all = 0


        #while step < len(batches):
        while step < 310:
            cla_input =[]

            batch = batches[step]
            step += 1
            decode_result = self._model.max_generator(self._sess, batch)

            example_list =[]
            #print("step", step)
            for i in range(FLAGS.batch_size):

                original_review = batch.original_reviews[i]  # string
                score = batch.score
                output_ids = [int(t) for t in decode_result['generated'][i]][:]
                decoded_words = data.outputids2words(output_ids, self._vocab, None)
                # Remove the [STOP] token from decoded_words, if necessary
                try:
                    fst_stop_idx = decoded_words.index(data.STOP_DECODING)  # index of the (first) [STOP] symbol
                    decoded_words = decoded_words[:fst_stop_idx]
                except ValueError:
                    decoded_words = decoded_words
                decoded_output = ' '.join(decoded_words)  # single string
                self.write_negtive_to_json(original_review, decoded_output, score, counter, path)
                counter += 1  # this is how many examples we've decoded
                cla_input.append(decoded_output)
                '''
                if len(original_review.split())>2 and len(decoded_output.split())>2:
                    list_ref.append([original_review.split()])
                    list_pre.append(decoded_output.split())
                '''
                #bleu.append(sentence_bleu([batch.original_reviews[i]], decoded_words_all.split()))
                if decoded_output.strip()=="":
                    decoded_output = ". "
                new_dis_example = bc.Example(decoded_output, batch.score, cla_batcher._vocab,
                                                      cla_batcher._hps)
                example_list.append(new_dis_example)

            cla_batch =  bc.Batch(example_list, cla_batcher._hps, cla_batcher._vocab)
            right_s,all_s,_,pre = model_class.run_eval_step(sess_cls,cla_batch)
            right += right_s
            all += all_s

            for i in range(FLAGS.batch_size):
                if len(batch.original_reviews[i].split())>2 and len(cla_input[i].split())>2 and batch.score == pre[i]:
                    list_ref.append([batch.original_reviews[i].split()])
                    list_pre.append(cla_input[i].split())

        transfer_acc = right*1.0/all *100
        bleu = corpus_bleu(list_ref,list_pre) * 100

        tf.logging.info("valid transfer acc: " + str(transfer_acc))
        tf.logging.info("BLEU: "+ str(bleu))

        return transfer_acc, bleu

    def generator_validation_positive_example(self, path, batcher, model_class, sess_cls, cla_batcher):

        if not os.path.exists(path): os.mkdir(path)

        shutil.rmtree(path)

        if not os.path.exists(path): os.mkdir(path)

        counter = 0
        step = 0

        t0 = time.time()
        batches = self.valid_batches

        list_ref = []
        list_pre = []
        right = 0
        all = 0

        while step < len(self.valid_batches):

            cla_input = []

            batch = batches[step]
            step += 1
            decode_result = self._model.max_generator(self._sess, batch)

            example_list = []

            for i in range(FLAGS.batch_size):

                original_review = batch.original_reviews[i]  # string
                score = batch.score
                output_ids = [int(t) for t in decode_result['generated'][i]][:]
                decoded_words = data.outputids2words(output_ids, self._vocab, None)
                # Remove the [STOP] token from decoded_words, if necessary
                try:
                    fst_stop_idx = decoded_words.index(data.STOP_DECODING)  # index of the (first) [STOP] symbol
                    decoded_words = decoded_words[:fst_stop_idx]
                except ValueError:
                    decoded_words = decoded_words
                decoded_output = ' '.join(decoded_words)  # single string
                self.write_negtive_to_json(original_review, decoded_output, score, counter, path)
                counter += 1  # this is how many examples we've decoded
                cla_input.append(decoded_output)

                if len(original_review.split()) > 2 and len(decoded_output.split()) > 2:
                    list_ref.append([original_review.split()])
                    list_pre.append(decoded_output.split())

                # bleu.append(sentence_bleu([batch.original_reviews[i]], decoded_words_all.split()))
                if decoded_output.strip() == "":
                    decoded_output = ". "
                new_dis_example = bc.Example(decoded_output, batch.score, cla_batcher._vocab,
                                                      cla_batcher._hps)
                example_list.append(new_dis_example)

            cla_batch = bc.Batch(example_list, cla_batcher._hps, cla_batcher._vocab)
            right_s, all_s, _, pre = model_class.run_eval_step(sess_cls, cla_batch)
            right += right_s
            all += all_s

            for i in range(FLAGS.batch_size):
                if len(batch.original_reviews[i].split())>2 and len(cla_input[i].split())>2 and batch.score == pre[i]:
                    list_ref.append([batch.original_reviews[i].split()])
                    list_pre.append(cla_input[i].split())

        tf.logging.info("valid acc: " + str(right * 1.0 / all))
        tf.logging.info("BLEU: " + str(corpus_bleu(list_ref, list_pre)))

    '''def compute_BLEU(self, train_step):

        counter = 0
        step = 0

        t0 = time.time()
        batches = self.valid_batches
        list_hop = []
        list_ref = []
        list_score = []

        while step <  500:

            batch = batches[step]
            step += 1

            decode_result = self._model.max_generator(self._sess, batch)

            for i in range(FLAGS.batch_size):

                original_review = batch.original_reviews[i]  # string
                #list_ref.append(original_review)
                #tf.logging.info (decode_result['generated'][0][i])
                output_ids = [int(t) for t in decode_result['generated'][i]][1:]
                decoded_words = data.outputids2words(output_ids, self._vocab, None)
                # Remove the [STOP] token from decoded_words, if necessary
                try:
                    fst_stop_idx = decoded_words.index(data.STOP_DECODING)  # index of the (first) [STOP] symbol
                    decoded_words = decoded_words[:fst_stop_idx]
                except ValueError:
                    decoded_words = decoded_words
                decoded_output = ' '.join(decoded_words)  # single string
                list_hop.append(decoded_output)
                list_ref.append(original_review)
                list_score.append(batch.labels[i])
                #self.write_negtive_to_json(original_review, decoded_output, counter)

                #counter += 1  # this is how many examples we've decoded
        file_temp = open(train_step+"_temp_result.txt",'w')
        for i, hop in enumerate(list_hop):
            file_temp.write(str(list_score[i])+": "+hop+"\n")
        file_temp.close()
       

        #print (new_sen_list)



        #bleu_score = corpus_bleu(new_ref_ref, new_sen_list)
        t1 = time.time()
        tf.logging.info('seconds for test generator: %.3f ', (t1 - t0))
        return 0'''

