from serveur import CustomServer
# from parser import HTTPParser, HTTPResponse

class CustomHTTPServer(CustomServer):
    def _start_message(self):
        print(f"Serveur démarré URL http://{self.host}:{self.port}/")

if __name__ == '__main__':
    server = CustomHTTPServer()
    server.start()
