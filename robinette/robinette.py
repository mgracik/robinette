from collections import defaultdict
import logging
import os
import pickle
import random
import time


DEFAULT_ORDER = 3
DEFAULT_SWAPWORDS = {}
DEFAULT_BANWORDS = []
DEFAULT_TIMEOUT = 3.0
DEFAULT_REPLIES = ['wat', ':)']


class Robinette(object):

    @staticmethod
    def tokenize(message):
        words = message.lower().split()
        # Remove the double quotes.
        words = [word.replace('"', '') for word in words]
        return words

    def __init__(self, order=DEFAULT_ORDER, swapwords=DEFAULT_SWAPWORDS,
                 banwords=DEFAULT_BANWORDS, timeout=DEFAULT_TIMEOUT):

        self.order = order
        self.swapwords = swapwords
        self.banwords = banwords
        self.timeout = timeout
        self.forward = defaultdict(list)
        self.backward = defaultdict(list)
        self.dummy_replies = set(DEFAULT_REPLIES)

    def communicate(self, message, learn=True, reply=True):
        words = self.tokenize(message)
        if learn:
            self.learn(words)
        if reply:
            return self.get_reply(words)

    def learn(self, words):
        if len(words) > self.order:
            self._add_chain(self.forward, words)
            self._add_chain(self.backward, list(reversed(words)))
        else:
            message = ' '.join(words)
            self.dummy_replies.add(message)

    def _add_chain(self, context, words):
        for i in range(len(words) - self.order):
            key = tuple(words[i:i + self.order])
            next_word = words[i + self.order]
            if next_word not in context[key]:
                context[key].append(next_word)

    def get_reply(self, words):
        keywords = self._get_keywords(words)
        if keywords:
            seed = random.choice(keywords)
            reply = self._generate_reply(seed)
            if reply and reply != words:
                return ' '.join(reply)
        return random.choice(list(self.dummy_replies))

    def _get_keywords(self, words):
        keywords = set()
        for word in words:
            word = self.swapwords.get(word, word)
            if word[0].isalnum() and word not in self.banwords:
                keywords |= set(k for k in self.forward if word in k)
        return list(keywords)

    def _generate_reply(self, seed):
        suffix = self._get_chain(self.forward, seed)
        suffix = suffix[self.order:] if suffix else []
        prefix = self._get_chain(self.backward, tuple(reversed(seed)))
        prefix.reverse()
        return prefix + suffix

    def _get_chain(self, context, start):
        words = list(start)
        starttime = time.time()
        while (time.time() - starttime) < self.timeout:
            if start in context:
                next_word = random.choice(context[start])
                words.append(next_word)
                start = tuple(words[-self.order:])
            else:
                break
        return words

    def train(self, messages):
        for message in messages:
            self.communicate(message['msg'], reply=False)
