from abc import ABC, abstractmethod


class ExporterPort(ABC):
    """
    Puerto de exportación. Los adaptadores concretos (Excel, TXT) implementan este contrato.
    Los casos de uso solo llaman a .export(data) sin saber el formato de destino.
    """

    @abstractmethod
    def export(self, data: list[dict], filename: str) -> bytes:
        """
        Serializa los datos y retorna el contenido en bytes listo para descarga.
        """
        ...
