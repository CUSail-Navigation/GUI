import torch
from torch import nn, optim
from collections import deque
import random
import numpy
import os

device = None

# TODO update the training function to work with the four input RL model
# (see simulator user manual)


class ReplayBuffer():
    def __init__(self, buffer_size):
        self.buffer_size = buffer_size
        self.num_exp = 0
        self.buffer = deque()

    def add(self, s, a, r, t, s2):
        experience = (s, a, r, t, s2)
        if self.num_exp < self.buffer_size:
            self.buffer.append(experience)
            self.num_exp += 1
        else:
            self.buffer.popleft()
            self.buffer.append(experience)

    def size(self):
        return self.buffer_size

    def count(self):
        return self.num_exp

    def sample(self, batch_size):
        if self.num_exp < batch_size:
            batch = random.sample(self.buffer, self.num_exp)
        else:
            batch = random.sample(self.buffer, batch_size)

        s, a, r, t, s2 = map(numpy.stack, zip(*batch))

        return s, a, r, t, s2

    def clear(self):
        self.buffer = deque()
        self.num_exp = 0


def fanin_(size):
    fan_in = size[0]
    weight = 1. / numpy.sqrt(fan_in)
    return torch.Tensor(size).uniform_(-weight, weight)


class Actor(nn.Module):
    def __init__(self, state_dim, action_dim, h1=400, h2=300, init_w=0.003):
        super(Actor, self).__init__()

        self.linear1 = nn.Linear(state_dim, h1)
        self.linear1.weight.data = fanin_(self.linear1.weight.data.size())

        self.ln1 = nn.LayerNorm(h1)

        self.linear2 = nn.Linear(h1, h2)
        self.linear2.weight.data = fanin_(self.linear2.weight.data.size())

        self.ln2 = nn.LayerNorm(h2)

        self.linear3 = nn.Linear(h2, action_dim)
        self.linear3.weight.data.uniform_(-init_w, init_w)

        self.relu = nn.ReLU()
        self.tanh = nn.Tanh()

    def forward(self, state):
        x = self.linear1(state)
        x = self.ln1(x)
        x = self.relu(x)

        x = self.linear2(x)
        x = self.ln2(x)
        x = self.relu(x)

        x = self.linear3(x)
        x = self.tanh(x)
        return x

    def get_action(self, state):
        state = torch.FloatTensor(state).unsqueeze(0).to(device)
        action = self.forward(state)
        return action.detach().cpu().numpy()[0]


class Critic(nn.Module):
    def __init__(self, state_dim, action_dim, h1=400, h2=300, init_w=3e-3):
        super(Critic, self).__init__()

        self.linear1 = nn.Linear(state_dim, h1)
        self.linear1.weight.data = fanin_(self.linear1.weight.data.size())

        self.ln1 = nn.LayerNorm(h1)

        self.linear2 = nn.Linear(h1 + action_dim, h2)
        self.linear2.weight.data = fanin_(self.linear2.weight.data.size())

        self.ln2 = nn.LayerNorm(h2)

        self.linear3 = nn.Linear(h2, 1)
        self.linear3.weight.data.uniform_(-init_w, init_w)

        self.relu = nn.ReLU()

    def forward(self, state, action):
        x = self.linear1(state)
        x = self.ln1(x)
        x = self.relu(x)

        x = self.linear2(torch.cat([x, action], 1))
        x = self.ln2(x)
        x = self.relu(x)

        x = self.linear3(x)

        return x


class RealWorldTrain:
    def __init__(self,
                 actor_path,
                 critic_path,
                 action_dim=2,
                 state_dim=9,
                 lr_actor=0.00001,
                 lr_critic=0.0001,
                 buffer_size=100000):
        # Use GPU if possible
        global device
        if torch.cuda.is_available():
            device = torch.device("cuda:0")
            print("Using device {}".format(torch.cuda.get_device_name(0)))
        else:
            print("No GPU detected. Training on CPU is not recommended.")
            device = torch.device("cpu")

        self.actor = Actor(state_dim, action_dim).to(device)
        self.critic = Critic(state_dim, action_dim).to(device)

        if actor_path != "":
            self.actor.load_state_dict(torch.load(actor_path))
        if critic_path != "":
            self.critic.load_state_dict(torch.load(critic_path))

        self.target_critic = Critic(state_dim, action_dim).to(device)
        self.target_actor = Actor(state_dim, action_dim).to(device)

        for target_param, param in zip(self.target_critic.parameters(),
                                       self.critic.parameters()):
            target_param.data.copy_(param.data)

        for target_param, param in zip(self.target_actor.parameters(),
                                       self.actor.parameters()):
            target_param.data.copy_(param.data)

        self.q_optimizer = optim.Adam(self.critic.parameters(), lr=lr_critic)
        self.policy_optimizer = optim.Adam(self.actor.parameters(),
                                           lr=lr_actor)

        self.MSE = nn.MSELoss()
        self.memory = ReplayBuffer(buffer_size)

        self.batch_size = 64
        self.buffer_start = 100
        self.gamma = 0.9
        self.tau = 0.001

        self.goal_threshold = 5

    def train(self, state, action, terminal, next_state):
        # calculate the reward for the episode
        # assume that terminal is true if the goal was reached
        # assume action is joint ranges in (-90 to 90, -30 to 30)
        dist_mult = 5.0
        vmg_mult = 1.0
        time_penalty = 3.0

        max_sail = 90.0
        max_rudder = 30.0

        reward = -1.0 * time_penalty
        orig_dist = numpy.sqrt(state[7]**2 + state[8]**2)
        new_dist = numpy.sqrt(next_state[8]**2 + next_state[8]**2)
        reward += dist_mult * (orig_dist - new_dist)

        disp = numpy.array([next_state[7], next_state[8]])
        disp = disp / new_dist if new_dist > 0.0 else numpy.zeros_like(disp)

        vel = numpy.array([next_state[0], next_state[1]])
        speed = numpy.linalg.norm(vel)
        vel = vel / speed if speed > 0.0 else numpy.zeros_like(vel)
        vmg = numpy.dot(vel, disp)
        reward += vmg_mult * vmg**3

        if terminal:
            reward = 100  #only terminal if reached goal

        action = action / numpy.array([max_sail, max_rudder])
        action = numpy.clip(action, -1, 1)

        # add this example to the training data
        self.memory.add(state, action, reward, terminal, next_state)
        print("Added step to replay buffer. Size is now {}.".format(
            self.memory.count()))

        # train on a batch of steps
        self.step()
        self.save_models('./')

    def step(self):
        if self.memory.count() > self.buffer_start:
            s_batch, a_batch, r_batch, t_batch, s2_batch = self.memory.sample(
                self.batch_size)

            s_batch = torch.FloatTensor(s_batch).to(device)
            a_batch = torch.FloatTensor(a_batch).to(device)
            r_batch = torch.FloatTensor(r_batch).unsqueeze(1).to(device)
            t_batch = torch.FloatTensor(
                numpy.float32(t_batch)).unsqueeze(1).to(device)
            s2_batch = torch.FloatTensor(s2_batch).to(device)

            # critic loss
            a2_batch = self.target_actor(s2_batch)
            target_q = self.target_critic(s2_batch, a2_batch)
            y = r_batch + (1.0 - t_batch) * self.gamma * target_q.detach()
            q = self.critic(s_batch, a_batch)

            self.q_optimizer.zero_grad()
            q_loss = self.MSE(q, y)
            q_loss.backward()
            self.q_optimizer.step()

            # actor loss
            self.policy_optimizer.zero_grad()
            policy_loss = -self.critic(s_batch, self.actor(s_batch))
            policy_loss = policy_loss.mean()
            policy_loss.backward()
            self.policy_optimizer.step()

            # soft update frozen target networks
            for target_param, param in zip(self.target_critic.parameters(),
                                           self.critic.parameters()):
                target_param.data.copy_(target_param.data * (1.0 - self.tau) +
                                        param.data * self.tau)

            for target_param, param in zip(self.target_actor.parameters(),
                                           self.actor.parameters()):
                target_param.data.copy_(target_param.data * (1.0 - self.tau) +
                                        param.data * self.tau)

            print("Successfully trained on a batch.")

    def save_models(self, results_dir):
        torch.save(self.actor.state_dict(),
                   os.path.join(results_dir, 'actor_base_trained.pickle'))
        torch.save(self.critic.state_dict(),
                   os.path.join(results_dir, 'critic_base_trained.pickle'))
