# Copyright The PyTorch Lightning team.
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
import os
from unittest import mock
from unittest.mock import MagicMock

import pytest

from pytorch_lightning import Trainer
from pytorch_lightning.demos.boring_classes import BoringModel
from pytorch_lightning.loggers import _MLFLOW_AVAILABLE, MLFlowLogger
from pytorch_lightning.loggers.mlflow import MLFLOW_RUN_NAME, resolve_tags


def mock_mlflow_run_creation(logger, experiment_name=None, experiment_id=None, run_id=None):
    """Helper function to simulate mlflow client creating a new (or existing) experiment."""
    run = MagicMock()
    run.info.run_id = run_id
    logger._mlflow_client.get_experiment_by_name = MagicMock(return_value=experiment_name)
    logger._mlflow_client.create_experiment = MagicMock(return_value=experiment_id)
    logger._mlflow_client.create_run = MagicMock(return_value=run)
    return logger


@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_logger_exists(client, _, tmpdir):
    """Test launching three independent loggers with either same or different experiment name."""

    run1 = MagicMock()
    run1.info.run_id = "run-id-1"
    run1.info.experiment_id = "exp-id-1"

    run2 = MagicMock()
    run2.info.run_id = "run-id-2"

    run3 = MagicMock()
    run3.info.run_id = "run-id-3"

    # simulate non-existing experiment creation
    client.return_value.get_experiment_by_name = MagicMock(return_value=None)
    client.return_value.create_experiment = MagicMock(return_value="exp-id-1")  # experiment_id
    client.return_value.create_run = MagicMock(return_value=run1)

    logger = MLFlowLogger("test", save_dir=tmpdir)
    assert logger._experiment_id is None
    assert logger._run_id is None
    _ = logger.experiment
    assert logger.experiment_id == "exp-id-1"
    assert logger.run_id == "run-id-1"
    assert logger.experiment.create_experiment.asset_called_once()
    client.reset_mock(return_value=True)

    # simulate existing experiment returns experiment id
    exp1 = MagicMock()
    exp1.experiment_id = "exp-id-1"
    client.return_value.get_experiment_by_name = MagicMock(return_value=exp1)
    client.return_value.create_run = MagicMock(return_value=run2)

    # same name leads to same experiment id, but different runs get recorded
    logger2 = MLFlowLogger("test", save_dir=tmpdir)
    assert logger2.experiment_id == logger.experiment_id
    assert logger2.run_id == "run-id-2"
    assert logger2.experiment.create_experiment.call_count == 0
    assert logger2.experiment.create_run.asset_called_once()
    client.reset_mock(return_value=True)

    # simulate a 3rd experiment with new name
    client.return_value.get_experiment_by_name = MagicMock(return_value=None)
    client.return_value.create_experiment = MagicMock(return_value="exp-id-3")
    client.return_value.create_run = MagicMock(return_value=run3)

    # logger with new experiment name causes new experiment id and new run id to be created
    logger3 = MLFlowLogger("new", save_dir=tmpdir)
    assert logger3.experiment_id == "exp-id-3" != logger.experiment_id
    assert logger3.run_id == "run-id-3"


@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_run_name_setting(client, _, tmpdir):
    """Test that the run_name argument makes the MLFLOW_RUN_NAME tag."""

    tags = resolve_tags({MLFLOW_RUN_NAME: "run-name-1"})

    # run_name is appended to tags
    logger = MLFlowLogger("test", run_name="run-name-1", save_dir=tmpdir)
    logger = mock_mlflow_run_creation(logger, experiment_id="exp-id")
    _ = logger.experiment
    client.return_value.create_run.assert_called_with(experiment_id="exp-id", tags=tags)

    # run_name overrides tags[MLFLOW_RUN_NAME]
    logger = MLFlowLogger("test", run_name="run-name-1", tags={MLFLOW_RUN_NAME: "run-name-2"}, save_dir=tmpdir)
    logger = mock_mlflow_run_creation(logger, experiment_id="exp-id")
    _ = logger.experiment
    client.return_value.create_run.assert_called_with(experiment_id="exp-id", tags=tags)

    # default run_name (= None) does not append new tag
    logger = MLFlowLogger("test", save_dir=tmpdir)
    logger = mock_mlflow_run_creation(logger, experiment_id="exp-id")
    _ = logger.experiment
    default_tags = resolve_tags(None)
    client.return_value.create_run.assert_called_with(experiment_id="exp-id", tags=default_tags)


@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_run_id_setting(client, _, tmpdir):
    """Test that the run_id argument uses the provided run_id."""

    run = MagicMock()
    run.info.run_id = "run-id"
    run.info.experiment_id = "experiment-id"

    # simulate existing run
    client.return_value.get_run = MagicMock(return_value=run)

    # run_id exists uses the existing run
    logger = MLFlowLogger("test", run_id=run.info.run_id, save_dir=tmpdir)
    _ = logger.experiment
    client.return_value.get_run.assert_called_with(run.info.run_id)
    assert logger.experiment_id == run.info.experiment_id
    assert logger.run_id == run.info.run_id
    client.reset_mock(return_value=True)


@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_log_dir(client, _, tmpdir):
    """Test that the trainer saves checkpoints in the logger's save dir."""

    # simulate experiment creation with mlflow client mock
    run = MagicMock()
    run.info.run_id = "run-id"
    client.return_value.get_experiment_by_name = MagicMock(return_value=None)
    client.return_value.create_experiment = MagicMock(return_value="exp-id")
    client.return_value.create_run = MagicMock(return_value=run)

    # test construction of default log dir path
    logger = MLFlowLogger("test", save_dir=tmpdir)
    assert logger.save_dir == tmpdir
    assert logger.version == "run-id"
    assert logger.name == "exp-id"

    model = BoringModel()
    trainer = Trainer(default_root_dir=tmpdir, logger=logger, max_epochs=1, limit_train_batches=1, limit_val_batches=3)
    assert trainer.log_dir == logger.save_dir
    trainer.fit(model)
    assert trainer.checkpoint_callback.dirpath == (tmpdir / "exp-id" / "run-id" / "checkpoints")
    assert set(os.listdir(trainer.checkpoint_callback.dirpath)) == {"epoch=0-step=1.ckpt"}
    assert trainer.log_dir == logger.save_dir


def test_mlflow_logger_dirs_creation(tmpdir):
    """Test that the logger creates the folders and files in the right place."""
    if not _MLFLOW_AVAILABLE:
        pytest.skip("test for explicit file creation requires mlflow dependency to be installed.")

    assert not os.listdir(tmpdir)
    logger = MLFlowLogger("test", save_dir=tmpdir)
    assert logger.save_dir == tmpdir
    assert set(os.listdir(tmpdir)) == {".trash"}
    run_id = logger.run_id
    exp_id = logger.experiment_id

    # multiple experiment calls should not lead to new experiment folders
    for i in range(2):
        _ = logger.experiment
        assert set(os.listdir(tmpdir)) == {".trash", exp_id}
        assert set(os.listdir(tmpdir / exp_id)) == {run_id, "meta.yaml"}

    class CustomModel(BoringModel):
        def on_train_epoch_end(self, *args, **kwargs):
            self.log("epoch", self.current_epoch)

    model = CustomModel()
    limit_batches = 5
    trainer = Trainer(
        default_root_dir=tmpdir,
        logger=logger,
        max_epochs=1,
        limit_train_batches=limit_batches,
        limit_val_batches=limit_batches,
    )
    trainer.fit(model)
    assert set(os.listdir(tmpdir / exp_id)) == {run_id, "meta.yaml"}
    assert "epoch" in os.listdir(tmpdir / exp_id / run_id / "metrics")
    assert set(os.listdir(tmpdir / exp_id / run_id / "params")) == model.hparams.keys()
    assert trainer.checkpoint_callback.dirpath == (tmpdir / exp_id / run_id / "checkpoints")
    assert os.listdir(trainer.checkpoint_callback.dirpath) == [f"epoch=0-step={limit_batches}.ckpt"]


@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_experiment_id_retrieved_once(client, tmpdir):
    """Test that the logger experiment_id retrieved only once."""
    logger = MLFlowLogger("test", save_dir=tmpdir)
    _ = logger.experiment
    _ = logger.experiment
    _ = logger.experiment
    assert logger.experiment.get_experiment_by_name.call_count == 1


@mock.patch("pytorch_lightning.loggers.mlflow.Metric")
@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_logger_with_unexpected_characters(client, _, __, tmpdir):
    """Test that the logger raises warning with special characters not accepted by MLFlow."""
    logger = MLFlowLogger("test", save_dir=tmpdir)
    metrics = {"[some_metric]": 10}

    with pytest.warns(RuntimeWarning, match="special characters in metric name"):
        logger.log_metrics(metrics)


@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_logger_with_long_param_value(client, _, tmpdir):
    """Test that the logger raises warning with special characters not accepted by MLFlow."""
    logger = MLFlowLogger("test", save_dir=tmpdir)
    value = "test" * 100
    key = "test_param"
    params = {key: value}

    with pytest.warns(RuntimeWarning, match=f"Discard {key}={value}"):
        logger.log_hyperparams(params)


@mock.patch("pytorch_lightning.loggers.mlflow.Metric")
@mock.patch("pytorch_lightning.loggers.mlflow.Param")
@mock.patch("pytorch_lightning.loggers.mlflow.time")
@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_logger_experiment_calls(client, _, time, param, metric, tmpdir):
    """Test that the logger calls methods on the mlflow experiment correctly."""
    time.return_value = 1

    logger = MLFlowLogger("test", save_dir=tmpdir, artifact_location="my_artifact_location")
    logger._mlflow_client.get_experiment_by_name.return_value = None

    params = {"test": "test_param"}
    logger.log_hyperparams(params)

    logger.experiment.log_batch.assert_called_once_with(
        run_id=logger.run_id, params=[param(key="test_param", value="test_param")]
    )

    metrics = {"some_metric": 10}
    logger.log_metrics(metrics)

    logger.experiment.log_batch.assert_called_with(
        run_id=logger.run_id, metrics=[metric(key="some_metric", value=10, timestamp=1000, step=0)]
    )

    logger._mlflow_client.create_experiment.assert_called_once_with(
        name="test", artifact_location="my_artifact_location"
    )


@pytest.mark.parametrize(
    "status,expected",
    [
        ("success", "FINISHED"),
        ("failed", "FAILED"),
        ("finished", "FINISHED"),
    ],
)
@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_logger_finalize(_, __, status, expected):
    logger = MLFlowLogger("test")

    # Pretend we are in a worker process and finalizing
    _ = logger.experiment
    assert logger._initialized

    logger.finalize(status)
    logger.experiment.set_terminated.assert_called_once_with(logger.run_id, expected)


@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
def test_mlflow_logger_finalize_when_exception(*_):
    logger = MLFlowLogger("test")

    # Pretend we are on the main process and failing
    assert logger._mlflow_client
    assert not logger._initialized
    logger.finalize("failed")
    logger.experiment.set_terminated.assert_not_called()

    # Pretend we are in a worker process and failing
    _ = logger.experiment
    assert logger._initialized
    logger.finalize("failed")
    logger.experiment.set_terminated.assert_called_once_with(logger.run_id, "FAILED")


@mock.patch("pytorch_lightning.loggers.mlflow._MLFLOW_AVAILABLE", return_value=True)
@mock.patch("pytorch_lightning.loggers.mlflow.MlflowClient")
@pytest.mark.parametrize("log_model", ["all", True, False])
def test_mlflow_log_model(client, _, tmpdir, log_model):
    """Test that the logger creates the folders and files in the right place."""
    # Get model, logger, trainer and train
    model = BoringModel()
    logger = MLFlowLogger("test", save_dir=tmpdir, log_model=log_model)
    logger = mock_mlflow_run_creation(logger, experiment_id="test-id")

    trainer = Trainer(
        default_root_dir=tmpdir,
        logger=logger,
        max_epochs=2,
        limit_train_batches=3,
        limit_val_batches=3,
    )
    trainer.fit(model)

    if log_model == "all":
        # Checkpoint log
        assert client.return_value.log_artifact.call_count == 2
        # Metadata and aliases log
        assert client.return_value.log_artifacts.call_count == 2

    elif log_model is True:
        # Checkpoint log
        client.return_value.log_artifact.assert_called_once()
        # Metadata and aliases log
        client.return_value.log_artifacts.assert_called_once()

    elif log_model is False:
        # Checkpoint log
        assert not client.return_value.log_artifact.called
        # Metadata and aliases log
        assert not client.return_value.log_artifacts.called
