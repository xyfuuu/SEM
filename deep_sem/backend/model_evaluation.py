import numpy as np
from sentence_transformers import SentenceTransformer

from .sem import SemModel


class ModelEvaluator:

    def __init__(self, variable_descriptions):
        model = SentenceTransformer('distiluse-base-multilingual-cased')
        features = model.encode(list(variable_descriptions.values()))
        self.variable_descriptions = variable_descriptions
        self.variable_embedded = {v: f for v, f in zip(variable_descriptions.keys(), features)}

    @staticmethod
    def evaluate_with_sem(model, data):
        # This is based on the prior knowledge from SEM
        for factor, variables in model['measurement_dict'].items():
            if len(variables) < 2:
                return None

        model = ModelEvaluator.dict2lavaan(model)
        sem = SemModel()

        fit_result = sem.fit_sem_model(model, data)
        if not fit_result['is_fitted']:
            return None

        measure_indexes = sem.evaluate_sem_model()
        if not measure_indexes['is_evaluated']:
            return None

        return measure_indexes

    # This is a helper function to convert model in python dictionary format to lavaan string format.
    # Before modifying, you need to understand lavaan syntax and the function `gluon2dict` in `search_space.py`.
    @staticmethod
    def _dict2str(data_dict, separator):
        data_lavaan = ''
        for parent in data_dict.keys():
            if not data_dict[parent]:
                continue

            related_nodes = ''
            for son in data_dict[parent]:
                if not related_nodes:
                    related_nodes += son
                else:
                    related_nodes += ' + ' + son

            data_lavaan += parent + ' ' + separator + ' ' + related_nodes + '\n'

        return data_lavaan

    @staticmethod
    def dict2lavaan(model):
        measurement_dict = model['measurement_dict']
        regressions_dict = model['regressions_dict']
        covariance_dict = model['covariance_dict']

        model_lavaan = ModelEvaluator._dict2str(measurement_dict, '=~') + \
                       ModelEvaluator._dict2str(regressions_dict, '~') + \
                       ModelEvaluator._dict2str(covariance_dict, '~~')

        return model_lavaan

    def _calculate_nlp_distance(self, model_compressed):
        model = model_compressed['measurement_dict']

        loss = 0
        for factor, variables in model.items():
            if not variables:
                continue

            factor_loss = 0
            for a in variables:
                for b in variables:
                    factor_loss += np.sum(np.square(self.variable_embedded[a] - self.variable_embedded[b]))
            factor_loss /= len(variables)
            loss += factor_loss

        reward = -loss

        return reward

    def evaluate_with_index(self, model, sem_indexes):
        if sem_indexes is None:
            return -2

        agfi = sem_indexes['agfi']
        rmsea = sem_indexes['rmsea']
        pvalue = sem_indexes['pvalue']
        nfi = sem_indexes['nfi']
        cfi = sem_indexes['cfi']
        rfi = sem_indexes['rfi']
        pgfi = sem_indexes['pgfi']
        # nlp_reward = self._calculate_nlp_distance(model)

        index = agfi - rmsea * 20 + pvalue * 10 + nfi + cfi + rfi + pgfi

        return index

    def evaluate(self, model, data, sem_indexes=None):
        if sem_indexes is None:
            sem_indexes = ModelEvaluator.evaluate_with_sem(model, data)

        index = self.evaluate_with_index(model, sem_indexes)

        return index
