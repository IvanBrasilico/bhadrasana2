class Interceptor():

    def __init__(self, user_name):
        self.user_name = user_name

    def __getattr__(self, attr):
        self.__check_perms(attr)
        return super(Interceptor, self).__getattr__(attr)

    def __check_perms(self, name):
        # Do anything that you need to do before simulating the method call
        print(self.user_name)


class TesteInterceptor(Interceptor):

    def print(self, *args):
        print(args)


if __name__ == '__main__':
    teste = TesteInterceptor('ivan')
    teste.print('teste')
    teste.inexistente()
