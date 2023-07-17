import socketio
import eventlet
from flask import Flask

sio = socketio.Server()

app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)


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

    @classmethod
    def show_rooms(cls):
        rooms = []
        for room in cls.rooms.values():
            rooms.append((room.room_id, room.room_name))
        return rooms

    @classmethod
    def generate_room_id(cls):
        if cls.queue_free_id:
            return cls.queue_free_id[0]
        else:
            return len(cls.rooms) + 1


class User:
    users = {}
    sid_uid = {}
    uid_sid = {}
    queue_free_id = []

    def __init__(self):
        self.user_id = User.generate_user_id()
        self.username = None
        self.is_online = True
        self.host_room = []
        self.rooms = []
        User.users[self.user_id] = self

    @staticmethod
    def generate_user_id():
        if User.queue_free_id:
            return User.queue_free_id[0]
        else:
            return len(User.users) + 1

    def create_room(self, room_name):
        room = Room(self.user_id, room_name)
        self.host_room.append(room)
        return room.room_id, room_name

    def choice_room(self, room_id):
        room = Room.rooms.get(room_id)
        if room:
            if room in self.rooms:
                return "already"
            room.members.append(self)
            self.rooms.append(room)
            return True
        else:
            return False

    def exit_room(self, room_id):
        room = Room.rooms.get(room_id)
        if room:
            room.members.remove(self)
            self.rooms.remove(room)
            return True
        else:
            return False

    def show_my_rooms(self):
        rooms = []
        for room in self.rooms:
            rooms.append((room.room_id, room.room_name))
        return rooms

    def del_room(self, room):
        if room in self.host_room:
            for member in room.members:
                member.exit_room(room.room_id)
            Room.queue_free_id.append(room.room_id)
            del Room.rooms[room.room_id]
            return True
        else:
            return False


@sio.on("connect")
def connect(sid, environ):
    user = User()
    User.sid_uid[sid] = user.user_id
    User.uid_sid[user.user_id] = sid
    sio.emit('message', to=sid,
             data={"message": f"Пользователь создан. Ваш id = {user.user_id}."})
    sio.emit('message', data={"message": f"Новый пользователь с id = {user.user_id}"})
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
                sio.emit('message', data={
                    "message": f"Пользователь с id = {User.users[User.sid_uid[sid]].user_id} авторизировался с user_id = {user.user_id}"})
                print(f"Пользователь авторизирован c user_id = {user.user_id}. "
                      f"Пользователь c user_id = {User.users[User.sid_uid[sid]].user_id} удален")
                User.queue_free_id.append(User.users[User.sid_uid[sid]].user_id)
                del User.users[User.sid_uid[sid]]
                del User.sid_uid[sid]
                User.sid_uid[sid] = user.user_id
                User.uid_sid[user.user_id] = sid
                user.is_online = True
                sio.emit('message', to=sid, data={"message": f"Авторизация выполнена."})

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


@sio.on('create_room')
def create_room(sid, data):
    try:
        room_name = data.get("room_name")
        if room_name:
            user = User.users.get(User.sid_uid[sid])
            room_id, room_name = user.create_room(room_name)
            sio.emit('message', data={
                "message": f"Пользователь с user_id = {user.user_id} создал комнату {room_name} с room_id = {room_id}"})
            print(f"Комната {room_name} с room_id = {room_id} создана.")
        else:
            raise ValueError
    except:
        sio.emit('message', to=sid, data={"message": f"Нужно отправить json-файл с ключом room_name"})
        print(f"Попытка создания комнаты")


@sio.on('choice_room')
def choice_room(sid, data):
    try:
        room_id = data.get("room_id")
        user = User.users.get(User.sid_uid[sid])
        answer = user.choice_room(int(room_id))
        if answer == "already":
            sio.emit('message', to=sid, data={"message": f"Вы уже в комнате {room_id}"})
            print(f"Попытка подключения к комнате")
        elif not answer:
            raise ValueError
        else:
            sio.emit('message', to=sid, data={"message": f"Вы подключились к комнате {room_id}"})
            print(f"Пользователь с user_id = {user.user_id} подключился к комнате {room_id}")
    except:
        sio.emit('message', to=sid,
                 data={"message": f"Нужно отправить json-файл с ключом room_id c id существующей комнаты"})
        print(f"Попытка подключения к комнате")


@sio.on('show_rooms')
def show_rooms(sid, data):
    user = User.users.get(User.sid_uid[sid])
    sio.emit('message', to=sid,
             data={"message": f"Мои комнаты:{user.show_my_rooms()}. Все комнаты: {Room.show_rooms()}"})
    print(f"Пользователь с user_id = {user.user_id} запросил список комнат")


@sio.on('del_room')
def del_room(sid, data):
    try:
        room_id = data.get("room_id")
        room = Room.rooms.get(int(room_id))
        if not room:
            print("1111")
            raise ValueError
        user = User.users.get(User.sid_uid[sid])
        if not user.del_room(room):
            raise ValueError
        else:
            sio.emit('message', data={"message": f"Комната с {room_id} была удалена"})
            print(f"Комната с room_id = {room_id} была удалена")
    except:
        sio.emit('message', to=sid,
                 data={
                     "message": f"Нужно отправить json-файл с ключом room_id c id существующей комнаты и вы должны быть ее хостом"})
        print(f"Попытка удаления комнаты")


@sio.on('exit_room')
def exit_room(sid, data):
    try:
        room_id = data.get("room_id")
        room = Room.rooms.get(int(room_id))
        if room:
            user = User.users.get(User.sid_uid[sid])
            user.rooms.remove(room)
            room.members.remove(user)
            sio.emit('message', to=sid,
                     data={
                         "message": f"Вы вышли из комнаты с room_id = {room_id}"})
            print(f"Пользователь с user_id = {user.user_id} вышел из комнаты с room_id = {room_id}")

    except:
        sio.emit('message', to=sid,
                 data={
                     "message": f"Для выхода нужно отправить json-файл с ключом room_id c id существующей комнаты"})
        print(f"Попытка выйти из комнаты пользователя с user_id = {User.sid_uid.get(sid)}")


@sio.on('send_message')
def send_message(sid, data):
    user = User.users.get(User.sid_uid[sid])
    try:
        room_id = data.get("room_id")
        user_id = data.get("user_id")
        message = data.get("message")
        if room_id == "all":
            sio.emit('message',
                     data={"message": f"Пользователь с user_id = {user.user_id}  отправил сообщение всем:{message}"})
            print(f"Пользователь с user_id = {user.user_id} отправил сообщение всем: {message}")
        elif not room_id:
            if user_id:
                for user_ in User.users.values():
                    if User.users.get(int(user_id)):
                        if user_.is_online:
                            user_sid = User.uid_sid.get(int(user_id))
                            print(user_sid)
                            print(User.uid_sid)
                            sio.emit('message', to=user_sid, data={
                                "message": f"Пользователь с user_id = {user.user_id}  отправил вам сообщение: {message}"})
                            print(
                                f"Пользователь с user_id = {user.user_id} отправил сообщение пользователю с user_id = {user_.user_id}: {message}")
                            break
                        else:
                            sio.emit('message', to=sid, data={
                                "message": f"Пользователь с user_id = {user.user_id} не в сети"})
                            print(f"Пользователь с user_id = {user.user_id} попытался отправить сообщение "
                                  f"пользователю с user_id = {user_.user_id}: {message}")
            else:
                raise ValueError
        else:
            room = Room.rooms.get(int(room_id))
            if room:
                if room in user.rooms:
                    for user_ in room.members:
                        sio.emit('message', to=User.uid_sid.get(user_.user_id), data={
                            "message": f"Пользователь с user_id = {user.user_id} отправил сообщение всем в комнате {room_id}:{message}"})
                        print(
                            f"Пользователь с user_id = {user.user_id} отправил сообщение всем в комнате {room_id}:{message}")
                else:
                    sio.emit('message', to=sid, data={
                        "message": f"Вы не состоите в комнате {room_id}"})
                    print(f"Пользователь с user_id = {user.user_id} попытался отправить сообщение в комнату {room_id}")

            else:
                raise ValueError
    except:
        sio.emit('message', to=sid,
                 data={"message": f"Неправильный запрос или такого пользователя/комнаты не существует"})
        print(f"Пользователь с user_id = {user.user_id} попытался отправить сообщение")


@sio.on('del_user')
def del_user(sid, data):
    user = User.users.get(User.sid_uid[sid])
    sio.emit('message', to=sid, data={"message": f"Пользователь с user_id = {user.user_id} удален"})
    print(f"Пользователь с user_id = {user.user_id} удален")
    sio.disconnect(sid)
    if user.rooms:
        for room in user.rooms:
            room.members.remove(user)
    User.queue_free_id.append(user.user_id)
    del User.sid_uid[sid]
    del User.uid_sid[user.user_id]
    del user


@sio.on('disconnect')
def disconnect(sid):
    user = User.users.get(User.sid_uid[sid])
    user.is_online = False
    sio.emit('message',
             data={"message": f"Пользователь с user_id = {user.user_id} отключился"})
    print(f"Пользователь с user_id = {user.user_id} отсоединился от сервера")
    del User.sid_uid[sid]
    del User.uid_sid[user.user_id]


@sio.event
def wrong_request(sid):
    user = User.users.get(User.sid_uid[sid])
    sio.emit('message', to=sid,
             data={"message": f"Неверно указано событие"})
    print(f"Пользователь с user_id = {user.user_id} неверно указал событие")


@app.route('/api/rooms')
def show_rooms():
    rooms = []
    for room in Room.rooms.values():
        rooms.append((room.room_name, len(room.members)))
    return rooms, 200


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
