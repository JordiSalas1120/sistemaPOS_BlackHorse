from abc import ABC, abstractmethod


class MessengerPort(ABC):
    """
    Puerto de mensajería. El adaptador de WhatsApp implementa este contrato.
    Si en el futuro se cambia a Telegram o email, solo se reemplaza el adaptador.
    """

    @abstractmethod
    async def send_message(self, phone: str, message: str) -> bool:
        """
        Envía un mensaje al número de teléfono indicado.
        Retorna True si el envío fue exitoso.
        """
        ...
