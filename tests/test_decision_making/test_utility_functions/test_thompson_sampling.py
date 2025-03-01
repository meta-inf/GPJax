# Copyright 2023 The GPJax Contributors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
from jax import config

config.update("jax_enable_x64", True)

from beartype.typing import Callable
import jax.numpy as jnp
import jax.random as jr
import pytest

from gpjax.dataset import Dataset
from gpjax.decision_making.test_functions.continuous_functions import (
    AbstractContinuousTestFunction,
    Forrester,
    LogarithmicGoldsteinPrice,
)
from gpjax.decision_making.utility_functions.thompson_sampling import ThompsonSampling
from gpjax.decision_making.utils import OBJECTIVE
from gpjax.gps import (
    ConjugatePosterior,
    NonConjugatePosterior,
    Prior,
)
from gpjax.kernels import RBF
from gpjax.likelihoods import (
    Gaussian,
    Poisson,
)
from gpjax.mean_functions import Zero
from gpjax.typing import KeyArray


def generate_dummy_conjugate_posterior(dataset: Dataset) -> ConjugatePosterior:
    kernel = RBF(lengthscale=jnp.ones(dataset.X.shape[1]))
    mean_function = Zero()
    prior = Prior(kernel=kernel, mean_function=mean_function)
    likelihood = Gaussian(num_datapoints=dataset.n)
    posterior = prior * likelihood
    return posterior


def generate_dummy_non_conjugate_posterior(dataset: Dataset) -> NonConjugatePosterior:
    kernel = RBF(lengthscale=jnp.ones(dataset.X.shape[1]))
    mean_function = Zero()
    prior = Prior(kernel=kernel, mean_function=mean_function)
    likelihood = Poisson(num_datapoints=dataset.n)
    posterior = prior * likelihood
    return posterior


@pytest.mark.filterwarnings(
    "ignore::UserWarning"
)  # Sampling with tfp causes JAX to raise a UserWarning due to some internal logic around jnp.argsort
def test_thompson_sampling_no_objective_posterior_raises_error():
    key = jr.PRNGKey(42)
    forrester = Forrester()
    dataset = forrester.generate_dataset(num_points=10, key=key)
    posterior = generate_dummy_conjugate_posterior(dataset)
    posteriors = {"CONSTRAINT": posterior}
    datasets = {OBJECTIVE: dataset}
    with pytest.raises(ValueError):
        ts_utility_builder = ThompsonSampling(num_features=100)
        ts_utility_builder.build_utility_function(
            posteriors=posteriors, datasets=datasets, key=key
        )


@pytest.mark.filterwarnings(
    "ignore::UserWarning"
)  # Sampling with tfp causes JAX to raise a UserWarning due to some internal logic around jnp.argsort
def test_thompson_sampling_no_objective_dataset_raises_error():
    key = jr.PRNGKey(42)
    forrester = Forrester()
    dataset = forrester.generate_dataset(num_points=10, key=key)
    posterior = generate_dummy_conjugate_posterior(dataset)
    posteriors = {OBJECTIVE: posterior}
    datasets = {"CONSTRAINT": dataset}
    with pytest.raises(ValueError):
        ts_utility_builder = ThompsonSampling(num_features=100)
        ts_utility_builder.build_utility_function(
            posteriors=posteriors, datasets=datasets, key=key
        )


@pytest.mark.filterwarnings(
    "ignore::UserWarning"
)  # Sampling with tfp causes JAX to raise a UserWarning due to some internal logic around jnp.argsort
def test_thompson_sampling_non_conjugate_posterior_raises_error():
    key = jr.PRNGKey(42)
    forrester = Forrester()
    dataset = forrester.generate_dataset(num_points=10, key=key)
    posterior = generate_dummy_non_conjugate_posterior(dataset)
    posteriors = {OBJECTIVE: posterior}
    datasets = {OBJECTIVE: dataset}
    with pytest.raises(ValueError):
        ts_utility_builder = ThompsonSampling(num_features=100)
        ts_utility_builder.build_utility_function(
            posteriors=posteriors, datasets=datasets, key=key
        )


@pytest.mark.parametrize("num_rff_features", [0, -1, -10])
@pytest.mark.filterwarnings(
    "ignore::UserWarning"
)  # Sampling with tfp causes JAX to raise a UserWarning due to some internal logic around jnp.argsort
def test_thompson_sampling_invalid_rff_num_raises_error(num_rff_features: int):
    key = jr.PRNGKey(42)
    forrester = Forrester()
    dataset = forrester.generate_dataset(num_points=10, key=key)
    posterior = generate_dummy_conjugate_posterior(dataset)
    posteriors = {OBJECTIVE: posterior}
    datasets = {OBJECTIVE: dataset}
    with pytest.raises(ValueError):
        ts_utility_builder = ThompsonSampling(num_features=num_rff_features)
        ts_utility_builder.build_utility_function(
            posteriors=posteriors, datasets=datasets, key=key
        )


@pytest.mark.parametrize(
    "test_target_function",
    [(Forrester()), (LogarithmicGoldsteinPrice())],
)
@pytest.mark.parametrize("num_test_points", [50, 100])
@pytest.mark.parametrize("key", [jr.PRNGKey(42), jr.PRNGKey(10)])
@pytest.mark.filterwarnings(
    "ignore::UserWarning"
)  # Sampling with tfp causes JAX to raise a UserWarning due to some internal logic around jnp.argsort
def test_thompson_sampling_utility_function_correct_shapes(
    test_target_function: AbstractContinuousTestFunction,
    num_test_points: int,
    key: KeyArray,
):
    dataset = test_target_function.generate_dataset(num_points=10, key=key)
    posterior = generate_dummy_conjugate_posterior(dataset)
    posteriors = {OBJECTIVE: posterior}
    datasets = {OBJECTIVE: dataset}
    ts_utility_builder = ThompsonSampling(num_features=100)
    ts_utility_function = ts_utility_builder.build_utility_function(
        posteriors=posteriors, datasets=datasets, key=key
    )
    test_key, _ = jr.split(key)
    test_X = test_target_function.generate_test_points(num_test_points, test_key)
    ts_utility_function_values = ts_utility_function(test_X)
    assert ts_utility_function_values.shape == (num_test_points, 1)


@pytest.mark.parametrize(
    "test_target_function",
    [(Forrester()), (LogarithmicGoldsteinPrice())],
)
@pytest.mark.parametrize("num_test_points", [50, 100])
@pytest.mark.parametrize("key", [jr.PRNGKey(42), jr.PRNGKey(10)])
@pytest.mark.filterwarnings(
    "ignore::UserWarning"
)  # Sampling with tfp causes JAX to raise a UserWarning due to some internal logic around jnp.argsort
def test_thompson_sampling_utility_function_same_key_same_function(
    test_target_function: AbstractContinuousTestFunction,
    num_test_points: int,
    key: KeyArray,
):
    dataset = test_target_function.generate_dataset(num_points=10, key=key)
    posterior = generate_dummy_conjugate_posterior(dataset)
    posteriors = {OBJECTIVE: posterior}
    datasets = {OBJECTIVE: dataset}
    ts_utility_builder_one = ThompsonSampling(num_features=100)
    ts_utility_builder_two = ThompsonSampling(num_features=100)
    ts_utility_function_one = ts_utility_builder_one.build_utility_function(
        posteriors=posteriors, datasets=datasets, key=key
    )
    ts_utility_function_two = ts_utility_builder_two.build_utility_function(
        posteriors=posteriors, datasets=datasets, key=key
    )
    test_key, _ = jr.split(key)
    test_X = test_target_function.generate_test_points(num_test_points, test_key)
    ts_utility_function_one_values = ts_utility_function_one(test_X)
    ts_utility_function_two_values = ts_utility_function_two(test_X)
    assert isinstance(ts_utility_function_one, Callable)
    assert isinstance(ts_utility_function_two, Callable)
    assert (ts_utility_function_one_values == ts_utility_function_two_values).all()


@pytest.mark.parametrize(
    "test_target_function",
    [(Forrester()), (LogarithmicGoldsteinPrice())],
)
@pytest.mark.parametrize("num_test_points", [50, 100])
@pytest.mark.parametrize("key", [jr.PRNGKey(42), jr.PRNGKey(10)])
@pytest.mark.filterwarnings(
    "ignore::UserWarning"
)  # Sampling with tfp causes JAX to raise a UserWarning due to some internal logic around jnp.argsort
def test_thompson_sampling_utility_function_different_key_different_function(
    test_target_function: AbstractContinuousTestFunction,
    num_test_points: int,
    key: KeyArray,
):
    dataset = test_target_function.generate_dataset(num_points=10, key=key)
    posterior = generate_dummy_conjugate_posterior(dataset)
    posteriors = {OBJECTIVE: posterior}
    datasets = {OBJECTIVE: dataset}
    sample_one_key = key
    sample_two_key, _ = jr.split(key)
    ts_utility_builder = ThompsonSampling(num_features=100)
    ts_utility_function_one = ts_utility_builder.build_utility_function(
        posteriors=posteriors, datasets=datasets, key=sample_one_key
    )
    ts_utility_function_two = ts_utility_builder.build_utility_function(
        posteriors=posteriors, datasets=datasets, key=sample_two_key
    )
    test_key, _ = jr.split(sample_two_key)
    test_X = test_target_function.generate_test_points(num_test_points, test_key)
    ts_utility_function_one_values = ts_utility_function_one(test_X)
    ts_utility_function_two_values = ts_utility_function_two(test_X)
    assert isinstance(ts_utility_function_one, Callable)
    assert isinstance(ts_utility_function_two, Callable)
    assert not (ts_utility_function_one_values == ts_utility_function_two_values).all()
