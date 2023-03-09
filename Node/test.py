import threading


def print_hello():
    print("hello world")
    threading.Timer(0.01, print_hello).start()


print_hello()
