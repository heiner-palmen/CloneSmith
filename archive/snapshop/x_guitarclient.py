import socket

def send_trigger():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #kqhadc4uitbodrep.myfritz.net
    #192.168.0.50
    client.connect(('kqhadc4uitbodrep.myfritz.net', 12345))  # Connect to the server IP and port

    trigger = "StartAction"  # Replace with your trigger
    print("sending trigger")
    client.send(trigger.encode('utf-8'))

    client.close()

if __name__ == "__main__":
    send_trigger()