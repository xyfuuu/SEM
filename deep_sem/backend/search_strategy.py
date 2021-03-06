import numpy as np
import autogluon as ag
import matplotlib.pyplot as plt

from ..frontend.output import PaintPicture
from ..frontend.progressbar import ProgressBar


class ModelSearcher:

    def __init__(self, search_space, model_evaluator, data, num_trials=100):
        space = search_space.fetch()

        @ag.args(**space)
        def evaluate_callback(config, reporter):
            indexes = config['indexes']
            model = search_space.gluon2dict(config)
            reward = model_evaluator.evaluate_with_index(model, indexes)
            return reward

        self.searcher = ProgressBar(evaluate_callback, data, search_space, 0.5,
                                    resource={'num_cpus': 1, 'num_gpus': 0},
                                    num_trials=num_trials,
                                    reward_attr='reward',
                                    controller_batch_size=4,
                                    controller_lr=5e-3)

        self.evaluator = model_evaluator
        self.searchSpace = search_space
        self.data = data

    def search(self, verbose=False):
        # Running this function might crash Python.
        # This problem is caused by the multiprocessing of the RL algorithm and lavaan in R.
        # But the numeric part has been take care of, so the result is not corrupted.

        self.searcher.run()
        self.searcher.exec()

        if verbose:
            print('Best config: {}, best reward: {}'.format(self.searcher.get_best_config(),
                                                            self.searcher.get_best_reward()))

    def print_topk_solution(self, k, graphviz=False):
        args = self.searcher.get_topk_config(k)

        if graphviz:
            models = [self.searchSpace.gluon2dict(arg) for arg in args]
            evaluation = [self.evaluator.evaluate_with_sem(model, self.data) for model in models]
            output_dialog = PaintPicture(models, evaluation, self.evaluator.variable_descriptions)
            output_dialog.exec()
        else:
            for rank, arg in enumerate(args):
                model = self.searchSpace.gluon2dict(arg)
                model_lavaan = self.evaluator.dict2lavaan(model)
                print('The %dth good model looks like:\n%s' % (rank, model_lavaan))

                reward = self.evaluator.evaluate(model, self.data)
                print('The reward is: %f' % reward)

    def print_best_solution(self, graphviz=False):
        self.print_topk_solution(1, graphviz)

    def plot_learning_curve(self):
        learning_curve = [v[0]['reward'] for v in self.searcher.training_history.values()]
        curve_smoothed = [np.max(learning_curve[i:i + 5]) for i in range(0, len(learning_curve), 5)]

        plt.plot(range(len(curve_smoothed)), curve_smoothed)
        plt.show()
