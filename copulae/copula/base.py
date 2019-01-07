from abc import ABC, abstractmethod
from collections import namedtuple
from typing import NamedTuple, Optional

import numpy as np

from copulae.copula.abstract import AbstractCopula
from copulae.estimators import CopulaEstimator, __estimator_params_docs__
from copulae.math_tools.misc import pseudo_obs
from copulae.types import Array
from copulae.utils import format_docstring

TailDep = NamedTuple('Lambda', lower=np.ndarray, upper=np.ndarray)

np.set_printoptions(linewidth=120)


class BaseCopula(AbstractCopula, ABC):
    """
    The base copula object. All implemented copulae should inherit this class as it creates a common API for the fit
    method.
    """

    def __init__(self, dim: int, name: str):
        super().__init__(dim, name)

    @format_docstring(params_doc=__estimator_params_docs__)
    def fit(self, data: np.ndarray, x0: np.ndarray = None, method='mpl', est_var=False, verbose=1,
            optim_options: dict = None):
        """
        Fit the copula with specified data

        {params_doc}
        :return: (float, float)
            Tuple containing parameters of the Gaussian Copula
        """
        data = self.pobs(data)

        CopulaEstimator(self, data, x0=x0, method=method, est_var=est_var, verbose=verbose, optim_options=optim_options)

    @property
    def tau(self):
        """
        Computes the Kendall's Tau for bivariate copulas

        :return: numpy array
            Kendall's Tau
        """
        raise NotImplementedError

    @property
    def rho(self):
        """
        Computes the Spearman's Rho for bivariate copulas
        :return: numpy array
            Spearman's Rho
        """
        raise NotImplementedError

    @property
    def lambda_(self) -> TailDep:
        """
        Computes the tail dependence index for bivariate copulas
        :return: named tuple
            Tail dependence index (lambda) with keys
                lower: numpy array
                upper: numpy array
        """
        Lambda = namedtuple('lambda', ['lower', 'upper'])
        return Lambda(*self.__lambda__)

    @property
    @abstractmethod
    def __lambda__(self):
        raise NotImplementedError

    def itau(self, tau: Array):
        """
        Computes the inverse Kendall's Tau

        The inverse tau is sometimes called the calibration function. Together with the inverse rho, it helps determine
        ("calibrate") the copula parameter (which must be 1-dimensional) given the values of Kendall's Tau and
        Spearman's Rho

        :param tau: numpy array
            numerical values of Kendall's tau in [-1, 1]
        :return:
        """
        raise NotImplementedError

    def irho(self, rho: Array):
        """
        Computes the inverse Spearman's Rho

        The inverse tau is sometimes called the calibration function. Together with the inverse rho, it helps determine
        ("calibrate") the copula parameter (which must be 1-dimensional) given the values of Kendall's Tau and
        Spearman's Rho

        :param rho: numpy array
            numerical values of Spearman's rho in [-1, 1].
        :return:
        """
        raise NotImplementedError

    @property
    def dtau(self, x: Optional[np.ndarray] = None):
        """
        Computes derivative of Kendall's Tau

        :param x: numpy array, optional
            1d vector to compute derivative of Kendall's Tau. If not supplied, will default to copulas parameters
        :return: numpy array
            Derivative of Kendall's Tau
        """
        raise NotImplementedError

    @property
    def drho(self, x: Optional[np.ndarray] = None):
        """
        Computes derivative of Spearman's Rho

        :param x: numpy array optional
            1d vector to compute derivative of Spearman's Rho. If not supplied, will default to copulas parameters
        :return: numpy array
            Derivative of Spearman's Rho
        """
        raise NotImplementedError

    def cdf(self, x: Array, log=False) -> np.ndarray:
        """
        Returns the cumulative distribution function (CDF) of the copulae.

        The CDF is also the probability of a RV being less or equal to the value specified. Equivalent to the 'p'
        generic function in R.

        :param x: numpy array of size (n x d)
            Vector or matrix of observed data
        :param log: bool
            If True, the probability 'p' is given as log(p)
        :return: numpy array
            The probability (CDF) of the RV
        """
        raise NotImplementedError

    def pdf(self, x: Array, log=False) -> np.ndarray:
        """
        Returns the probability distribution function (PDF) of the copulae.

        The PDF is also the density of the RV at for the particular distribution. Equivalent to the 'd' generic function
        in R.

        :param x: numpy array of size (n x d)
            Vector or matrix of observed data
        :param log: bool
            If True, the density 'd' is given as log(d)
        :return: numpy array
            The density (PDF) of the RV
        """
        raise NotImplementedError

    @property
    def params(self):
        """
        The parameter set which describes the copula

        :return: numpy array:
            parameters of the copulae
        """
        raise NotImplementedError

    @params.setter
    def params(self, params: Array):
        """
        Sets the parameter which describes the copula

        :param params: numpy array:
            parameters of the copulae
        """
        raise NotImplementedError

    def log_lik(self, data: np.ndarray) -> float:
        """
        Returns the log likelihood (LL) of the copula.

        The greater the LL (closer to inf) the better.

        :param data: numpy array
            Data set used to calculate the log likelihood
        :return: float
            Log likelihood
        """
        return self.pdf(data, log=True).sum()

    def concentration_down(self, x):
        """
        Returns the theoretical lower concentration function.

        Parameters
        ----------
        x : float (between 0 and 0.5)
        """
        if x > 0.5 or x < 0:
            raise ValueError("The argument must be included between 0 and 0.5.")
        return self.cdf([x, x]) / x

    def concentration_up(self, x):
        """
        Returns the theoretical upper concentration function.

        Parameters
        ----------
        x : float (between 0.5 and 1)
        """
        if x < 0.5 or x > 1:
            raise ValueError("The argument must be included between 0.5 and 1.")
        return (1. - 2 * x + self.cdf([x, x])) / (1. - x)

    def concentration_function(self, x):
        """
        Returns the theoretical concentration function.

        Parameters
        ----------
        x : float (between 0 and 1)
        """
        if x < 0 or x > 1:
            raise ValueError("The argument must be included between 0 and 1.")
        if x < 0.5:
            return self.concentration_down(x)
        return self.concentration_up(x)

    @staticmethod
    def pobs(data: np.ndarray, ties='average'):
        """
        Compute the pseudo-observations for the given data matrix

        :param data: numpy array
            n x d-matrix (or d-vector) of random variates to be converted to pseudo-observations

        :param ties: str
            string specifying how ranks should be computed if there are ties in any of the coordinate samples                    The options are 'average', 'min', 'max', 'dense' and 'ordinal'. Passed to scipy.stats.rankdata

        :return: numpy array
            matrix or vector of the same dimension as X containing the pseudo observations
        """
        return pseudo_obs(data, ties)

    def random(self, n: int, seed: int = None):
        """
        Generate random observations for the copula

        Equivalent to the 'r' generic function in R.

        :param n: int
            number of observations to be generated
        :param seed: int, optional
            seed for the random generator
        :return: numpy array (n x d)
            array of generated observations
        """

        if self.fit_stats is None:
            raise RuntimeError("Copula must be fitted before it can generate random numbers")

        return self.__random__(n, seed)

    @abstractmethod
    def __random__(self, n: int, seed: int = None):
        raise NotImplementedError

    @abstractmethod
    def summary(self):
        """
        Prints information about the copula
        """
        raise NotImplementedError