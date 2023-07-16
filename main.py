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
    sid_uid = {}
    queue_free_id = []


    def __init__(self):
        self.user_id = User.generate_user_id()
        self.username = None
        self.is_online = True
        self.host_room = None
        self.room = None
        User.users[self.user_id] = self

    @staticmethod
    def generate_user_id():
        if User.queue_free_id:
            return User.queue_free_id[0]
        else:
            return len(User.users) + 1

    def create_room(self, room_name):
        pass

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



@sio.event
def connect(sid, environ):
    user = User()
    User.sid_uid[sid] = user.user_id
    sio.emit('message', to=sid, data={"message": f"Пользователь создан. Ваш id = {user.user_id}"})
    print(f"Пользователь c user_id = {user.user_id} создан.")
    lst_users = []
    for user in User.users.values():
        lst_users.append((user.user_id, user.username, user.is_online))
    print(f"Пользователи на сервере: {lst_users}")


@sio.on('auth')
def auth(sid, data):
    try:
        user_id = int(data.get("user_id"))
        if not User.users.get(user_id):
            sio.emit('message', to=sid, data={"message": f"Пользователя с таким user_id нет"})
            print(f"Попытка авторизации")
        else:
            user = User.users.get(user_id)
            if user.is_online:
                sio.emit('message', to=sid, data={"message": f"Пользователь уже онлайн"})
                print(f"Попытка авторизации")
            else:
                print(f"Пользователь авторизирован c user_id = {user.user_id}. "
                      f"Пользователь c user_id = {User.users[User.sid_uid[sid]].user_id} удален")
                User.queue_free_id.append(User.users[User.sid_uid[sid]].user_id)
                del User.users[User.sid_uid[sid]]
                del User.sid_uid[sid]
                User.sid_uid[sid] = user.user_id
                user.is_online = True
                sio.emit('message', to=sid, data={"message": f"Авторизация выполнена"})
    except ValueError:
        sio.emit('message', to=sid, data={"message": f"Нужно отправить число"})
        print(f"Попытка авторизации")
    except (TypeError, AttributeError):
        sio.emit('message', to=sid, data={"message": f"Нужно отправить json-файл с ключом user_id"})
        print(f"Попытка авторизации")



@sio.on('change_name')
def change_name(sid, data):
    username = data.get("username")
    if username:
        user = User.users.get(User.sid_uid[sid])
        print(f"Пользователь с user_id = {user.user_id} сменил имя с {user.username} на {username}")
        user.username = username
        sio.emit('message', to=sid, data={"message": f"Имя успешно изменено на {username}"})
    else:
        sio.emit('message', to=sid, data={"message": f"Нужно отправить json-файл с ключом username"})
        print(f"Попытка смены имени")



# @sio.on('create_room')
# def create_room(sid):
#     user =
#     room = Room(U)
#
# @sio.on('del_room')
# def del_room(sid):
#     pass

@sio.on('del_user')
def del_user(sid, data):
    user = User.users.get(User.sid_uid[sid])
    sio.emit('message', to=sid, data={"message": f"Пользователь с user_id = {user.user_id} удален"})
    print(f"Пользователь с user_id = {user.user_id} удален")
    sio.disconnect(sid)
    User.queue_free_id.append(user.user_id)
    del user

@sio.on('disconnect')
def disconnect(sid):
    user = User.users[User.sid_uid[sid]]
    user.is_online = False
    del User.sid_uid[sid]


eventlet.wsgi.server(eventlet.listen(('', 5000)), app
                     )
