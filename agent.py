import torch.nn as nn
import numpy as np

from torch.autograd import Variable
from torch.optim import Adam

from utils import FloatTensor, LongTensor


class Agent(object):
    def __init__(self, play_strategy, learn_strategy):
        self.play_strategy = play_strategy
        self.learn_strategy = learn_strategy

    def select_action(self, state):
        return self.play_strategy.select_action(state)

    def learn(self):
        return self.learn_strategy.learn()


class GreedyStrategy(object):
    def __init__(self, Q, cuda=True):
        self.Q = Q.cuda() if cuda else Q
        self.cuda = cuda

    def select_action(self, state):
        state = state[None, ...]
        state = FloatTensor(state, self.cuda)
        state = Variable(state, requires_grad=False)

        values = self.Q(state)

        _, action = values.max(dim=1)
        return action.data.cpu().numpy()


class RandomStrategy(object):
    def __init__(self, num_actions):
        self.num_actions = num_actions

    def select_action(self, _):
        return np.random.choice(self.num_actions, size=1, replace=False)


class EpsilonGreedyStrategy(object):
    def __init__(self, Q, num_actions, decay):
        self.decay = decay
        self.random_strategy = RandomStrategy(num_actions)
        self.greedy_strategy = GreedyStrategy(Q)

    def select_action(self, state):
        decay_value = self.decay()
        random_value = np.random.random(size=1)

        if random_value < decay_value:
            return self.random_strategy.select_action(state)
        else:
            return self.greedy_strategy.select_action(state)


class NoLearnStrategy(object):
    def learn(self):
        pass


class QLearningStrategy(object):
    def __init__(self, Q, lr, replay, gamma, batch_size, cuda=True):
        self.Q = Q.cuda() if cuda else Q
        self.lr = lr
        self.cuda = cuda
        self.gamma = gamma
        self.batch_size = batch_size
        self.criterion = nn.MSELoss()
        self.optimizer = Adam(Q.parameters(), lr=lr)
        self.replay = replay

    def learn(self):
        prev_states, actions, rewards, states = self.replay.sample_minibatch(self.batch_size)

        rewards = FloatTensor(rewards[:, None], self.cuda)
        rewards = Variable(rewards, requires_grad=False)

        actions = LongTensor(actions[:, None], self.cuda)
        actions = Variable(actions, requires_grad=False)

        prev_states = FloatTensor(prev_states, self.cuda)
        prev_states = Variable(prev_states, requires_grad=False)

        states = FloatTensor(states, self.cuda)
        states = Variable(states, requires_grad=False)

        current_values = self.Q(prev_states)
        current_values = current_values.gather(dim=1, index=actions)

        values, _ = self.Q(states).max(dim=1, keepdim=True)
        target_values = rewards + self.gamma * values
        target_values = target_values.detach()

        loss = self.criterion(current_values, target_values)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()