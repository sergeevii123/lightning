from lightning_app.utilities.imports import _is_pytorch_lightning_available, _is_torch_available

if _is_torch_available():
    from torch.utils.data import Dataset

if _is_pytorch_lightning_available():
    from torchmetrics import Metric

    from lightning_fabric import Fabric
    from pytorch_lightning import LightningDataModule, LightningModule, Trainer
    from pytorch_lightning.accelerators.accelerator import Accelerator
    from pytorch_lightning.callbacks import Callback
    from pytorch_lightning.lite import LightningLite
    from pytorch_lightning.loggers import Logger
    from pytorch_lightning.loops import Loop
    from pytorch_lightning.plugins import PrecisionPlugin
    from pytorch_lightning.profilers import Profiler


if __name__ == "__main__":

    class RandomDataset(Dataset):
        pass

    class BoringDataModule(LightningDataModule):
        pass

    class BoringModel(LightningModule):
        pass

    class BoringTrainer(Trainer):
        pass

    class BoringPrecisionPlugin(PrecisionPlugin):
        pass

    class BoringAccelerator(Accelerator):
        pass

    class BoringCallback(Callback):
        pass

    class BoringLogger(Logger):
        pass

    class BoringLoop(Loop):
        pass

    class BoringMetric(Metric):
        pass

    class BoringLightningLite(LightningLite):
        pass

    class BoringFabric(Fabric):
        pass

    class BoringProfiler(Profiler):
        pass
