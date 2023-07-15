import socketio
import eventlet

sio = socketio.Server()

app = socketio.WSGIApp(sio)


class Room:
    # Создаем список комнат и очередь свободных id
    rooms = {}
    queue_free_id = []

    def __init__(self, room_host, room_name):
        # При инициализации выдается название комнаты и id
        self.room_name = room_name
        self.room_id = Room.generate_room_id()
        self.room_host = room_host
        self.members = []
        Room.rooms[self.room_id] = self

    def del_room(self, user_id):
        # Метод для удаления комнаты
        for room in Room.rooms:
            if room.room_id == self.room_id:
                Room.queue_free_id.append(self.room_id)
                del Room.rooms[self.room_id]
                print(f"Комната с id: {self.room_id} удалена и все пользователи были отключены")
                break

    @staticmethod
    def generate_room_id():
        if Room.queue_free_id:
            return Room.queue_free_id[0]
        else:
            return len(Room.rooms) + 1


# room1 = Room("Egor", "Roomcha")
# print(Room.rooms)
# room2 = Room("Fedya", "Roomcha2")
# for room in Room.rooms:
#     print(room.room_name)
# room1.del_room()
# print(Room.rooms)


class User:
    users = {}
    queue_free_id = []

    def __init__(self, sid, username):
        self.user_id = User.generate_user_id()
        self.username = username
        self._sid = sid
        self.room = None
        self.is_online = True
        User.users[self.user_id] = self

    @property
    def sid(self):
        return self._sid

    @sid.setter
    def sid(self, sid):
        self._sid = sid

    @staticmethod
    def generate_user_id():
        if User.queue_free_id:
            return User.queue_free_id[0]
        else:
            return len(User.users) + 1

    def choise_room(self, room_id):
        if room_id is None:
            self.room = None
            return
        for room in Room.rooms:
            if room.room_id == room_id:
                room.members.append(self)
                self.room = room
                return
        if Room.rooms:
            print("Комнаты с таким id нет, нужно выбрать другой id")
        return None

    def del_room(self):
        # Метод для удаления пользователя
        for room in Room.rooms:
            if room.room_id == self.room_id:
                Room.queue_free_id.append(self.room_id)
                Room.rooms.remove(room)
                print(f"Комната с id: {self.room_id} удалена и все пользователи были отключены")
                break


@sio.event
def connect(sid, environ):
    query_string = environ['QUERY_STRING']
    params = {k.strip(): v.strip() for k, v in [pair.split('=') for pair in query_string.split('&')]}
    user_id = params.get('user_id')
    if params.get('user_name'):
        user_name = params.get('user_name')
    else:
        user_name = "Человек"
    if User.users.get(user_id):
        user = User.users.get(user_id)
        user.sid = sid
        sio.emit('message', to=sid, data={"message": f"С возвращением {user.username}"})
    else:
        user = User(sid, user_name)
        sio.emit('message', to=sid, data={"message": f"Пользователь {user.username, user.user_id} создан"})


# @sio.on('change_name')
# def change_name(sid):
#     pass
#
# @sio.on('create_room')
# def create_room(sid):
#     user =
#     room = Room(U)
#
# @sio.on('del_room')
# def del_room(sid):
#     pass

@sio.on('disconnect')
def disconnect(sid):
    pass


eventlet.wsgi.server(eventlet.listen(('', 5000)), app
                     )
