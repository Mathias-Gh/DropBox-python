class ProtocolError(Exception):
    pass


class Message:
    def __init__(self, command, args):
        self.command = command
        self.args = args


class ProtocolParser:
    @staticmethod
    def parse(raw):
        if not raw:
            raise ProtocolError("Message vide")

        parts = raw.strip().split("|")
        command = parts[0].upper()
        args = parts[1:]

        return Message(command, args)
