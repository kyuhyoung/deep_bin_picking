"""Support for implementation of policies, and baseline policies."""
import contextlib
import logging
import os
import math
import random
import argparse
import pdb

from env.scene import Scene, ScenePopulator
from env.crate import Action, CrateMDP
from env.action_finder import Action, ActionFinder

class Policy(object):
    def __init__(self, env):
        self.env = env

    def choose_action(self, state):
        pass

class PolicyRunner(object):
    def __init__(self, scene, scene_populator, env, policy, discount=0.9):
        self.scene = scene
        self.scene_populator = scene_populator
        self.env = env
        self.policy = policy
        self.discount = discount

    def start_episode(self):
        self.state = self.env.reset()
        self.discounted_return = 0
        self.step = 0

    def step_episode(self):
        action = self.policy.choose_action(self.state)
        if action == None:
            return False
        logging.info('Attempting to remove item {}...'.format(action.item_id))
        (state, reward, done) = self.env.step(action)
        logging.info('Received reward {}'.format(reward))
        self.state = state
        self.discounted_return += math.pow(self.discount, self.step) * reward
        self.step += 1
        return not done

    def run_episode(self):
        self.start_episode()
        while self.step_episode():
            pass
        return self.discounted_return

@contextlib.contextmanager
def returns_log(filepath=None, description=None):
    file = None
    if filepath is not None:
        file = open(filepath, 'w')
        file.write('Discounted returns in episodes\n')
        if description is not None:
            file.write('{}\n'.format(description))
    yield file
    if file is not None:
        file.close()


class PolicyTester(object):
    def __init__(self, policy_runner, returns_logfile, num_episodes=100):
        self.policy_runner = policy_runner
        self.num_episodes = num_episodes
        self.episode = 0
        self.total_discounted_returns = 0
        self.average_discounted_returns = 0
        self.returns_logfile = returns_logfile

    def run_episode(self):
        logging.info('Running episode {}...'.format(self.episode))
        discounted_return = self.policy_runner.run_episode()
        self.total_discounted_returns += discounted_return
        self.average_discounted_returns = self.total_discounted_returns / (self.episode + 1)
        logging.info('Episode {} accumulated a discounted return of {}'.format(
            self.episode + 1, discounted_return
        ))
        logging.info('Average reward per episode over past {} episodes: {}'.format(
            self.episode + 1, self.average_discounted_returns
        ))
        if self.returns_logfile is not None:
            self.returns_logfile.write('{} {} {}\n'.format(
                self.episode + 1, discounted_return, self.average_discounted_returns
            ))
            self.returns_logfile.flush()
        self.episode += 1

    def run_episodes(self):
        logging.info('Running {} episodes...'.format(self.num_episodes))
        while (self.episode < self.num_episodes):
            self.run_episode()

class HighestFirstBaseline(Policy):
    def choose_action(self, state):
        item_heights = {item: pose[0][2] for (item, pose) in state['poses'].items()}
        if len(item_heights) == 0:
            return None
        item_id = max(item_heights, key=item_heights.get)
        return Action(item_id, state['item_names'][item_id], None, 1.0)

class LowestFirstBaseline(Policy):
    def choose_action(self, state):
        item_heights = {item: pose[0][2] for (item, pose) in state['poses'].items()}
        if len(item_heights) == 0:
            return None
        item_id = min(item_heights, key=item_heights.get)
        return Action(item_id, state['item_names'][item_id], None, 1.0)

class RandomBaseline(Policy):
    def choose_action(self, state):
        # TODO: only choose from available actions
        (item_id, item_name) = random.choice(list(state['poses'].items()))
        return Action(item_id, item_name, None, None)

class GreedyBaseline(Policy):
    def choose_action(self, state):
        # TODO: implement a greedy baseline
        (item_id, item_name) = random.choice(list(state['poses'].items()))
        return Action(item_id, item_name, None, None)


BASELINE_POLICIES = {
    'baseline_highest': HighestFirstBaseline,
    'baseline_lowest': LowestFirstBaseline,
    'baseline_random': RandomBaseline,
    'baseline_greedy': GreedyBaseline
}


def test_policy(policy_name, Policy,
                policy_factory_args=[], policy_factory_kwargs={}):
    """Run a policy on the CrateMDP environment."""
    scene = Scene(show_gui=False)
    scene_populator = ScenePopulator(scene)
    simple_done = (policy_name == 'baseline_lowest' or
                   policy_name == 'baseline_highest')
    env = CrateMDP(scene, scene_populator, simple_done=simple_done)
    policy = Policy(env, *policy_factory_args, **policy_factory_kwargs)
    policy_runner = PolicyRunner(scene, scene_populator, env, policy)
    if not os.path.exists('results/{}'):
        os.makedirs('results/{}')
    with returns_log('results/{}/results.txt'.format(policy_name)) as f:
        policy_tester = PolicyTester(policy_runner, f)
        policy_tester.run_episodes()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'policy', type=str, choices=BASELINE_POLICIES.keys(),
        help='The baseline policy to test.'
    )
    args = parser.parse_args()
    test_policy(args.policy, BASELINE_POLICIES[args.policy])


if __name__ == '__main__':
    main()
