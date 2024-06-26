import re, datetime

from open_folder import OpenFolder

class UserCorespondence(OpenFolder):

    def _files_info(self, filename):
        self.data = list(map(self.__replace_brake, self._open_txt(filename)))

        self.__suspect_name: dict = self.__get_suspect_name(self.data)
        self.__suspect_period: datetime = self.__get_suspect_period(self.data)

        return self.__get_form_info(self.suspect_name, filename)

    def _get_messages(self, filename) -> dict:

        self._files_info(filename)
        self.__messages_dict = self._select_messages(self.data, self.__suspect_name)

        return self.__messages_dict
        
    def __get_form_info(self, name, path):
        name = name["name"]
        period = " - ".join(list(map(lambda string: string.split()[0], self.suspect_period)))
        filename = re.search("(?<=\/)[\w\d0-1_\.\s-]*\.txt", path).group()
        return name, period, filename

    def _select_messages(self, data, suspect_name) -> dict:
        """перебираем весь файл, получаем стартовые и конечные точки сообщения и формируем объект Message"""
        num_line = 0
        start_message = 0
        message_dict = {}

        message_count = 0

        while num_line != len(data):
            if data[num_line].replace("\n","") in ("От кого:", "Кому:"):
                if start_message == 0:
                    start_message = num_line
                 
                else:
                    message = Message(data[start_message : num_line], suspect_name)
                    start_message = num_line

            elif num_line == len(data) - 1:
                message = Message(data[start_message : num_line], suspect_name)
            
            
            if "message" in locals():
                if isinstance(self, Message):   # если вызывается из объекта Message возвращаем сформированный объект класса Message
                    return message
                message_count += 1
                if message not in message_dict:
                    message_dict[message] = [message]
                else:
                    message_dict[message].append(message)
                del message

            
            num_line += 1


        return message_dict

    def __replace_brake(self, line) -> str:
        if line != "\n":
            line = line.replace("\n", "")

        return line

    def __get_suspect_name(self, data: str) -> None:
        for string in data:
            if re.search("^http[s]?://vk.com/[\w\d]+.+\(.+\)", string):
                data = re.search("^http[s]?://vk.com/[\w\d]+.+\(.+\)", string).group()
                break

        name = " ".join((data.replace("(","").replace(")","").split()[-2:]))
        url = data.split()[0]

        return dict(zip(("name", "url"), (name, url)))

    def __get_suspect_period(self, data: list) -> datetime:
        for string in data:
            if re.search("Сообщения\sза\sпериод\s[\d.\s:-]+", string):
                data = re.search("Сообщения\sза\sпериод\s[\d.\s:-]+", string).group()
                break

        data = data.split()[3:]
        start_date = " ".join(data[:2])
        end_date = " ".join(data[-2:])
            
        return datetime.datetime.strptime(start_date, '%d.%m.%Y %H:%M:%S'), datetime.datetime.strptime(end_date, '%d.%m.%Y %H:%M:%S')

    def __getitem__(self, item) -> list:
        data_dict = self.messages
        if item.isdigit() and list(filter(lambda x: x.chat_id == item, data_dict)):
            key = list(filter(lambda x: x.chat_id == item, data_dict))[0]
            return data_dict[key]
        
        elif list(filter(lambda x: x.user_name["name"] == item, data_dict)):
            key = list(filter(lambda x: x.user_name["name"] == item, data_dict))[0]
            return data_dict[key]
        
        else:
            return []

    def __len__(self) -> int:
        return len(self.__messages_dict)

    def __iter__(self):
        self.user_count = 0
        self.users_iter_tuple = tuple(self.__messages_dict.keys())
        return self
    
    def __next__(self):
        if self.user_count < len(self.users_iter_tuple):
            self.user_count += 1
            return self.__messages_dict[self.users_iter_tuple[self.user_count - 1]]
        else:
            raise StopIteration

    @property
    def messages(self) -> dict:
        return self.__messages_dict

    @property
    def suspect_name(self) -> dict:
        return self.__suspect_name
    
    @property
    def suspect_period(self) -> list:
        return list(map(lambda x: x.strftime("%d.%m.%Y %H:%M:%S"), self.__suspect_period))

class Message(UserCorespondence):

    def __init__(self, message: list, suspect_name: dict):
        self.__message_lst = message
        self.__suspect_name = suspect_name

        self.__is_user = False
        self.__is_group = False
        self._is_forward = False

        self.__is_chat = False
        self.__chat_id = ""

        self.__message_type: str = self.__set_type(self.__message_lst[0])
        self.__message_recipient: dict = self.__set_recipient(self.__message_lst[1])
        self.__message_period: datetime = self.__set_period(self.__message_lst[2])

        self.__message_photo:list = []
        self.__message_other_files: list = []
        self.__message_links: list = []

        self.__message_audio: dict = {}     
        self.__message_video: dict = {}
        self.__message_wall: dict = {}

        self.__message_voice: str = ""
        self.__message_sticker: str = ""
        self.__message_gift: str = ""

        self.__message_forward: list = []

        self.__message_text: list = self.__set_text(self.__message_lst[3:])

    def __set_type(self, data) -> str:
        return "Входящий" if "От кого:" in data else "Исходящий"
    
    def __set_recipient(self, data) -> dict:
        data = data.replace("(", "").replace(")", "")

        name = ""
        url = ""

        if "https:" in data:
            name = " ".join(data.split()[1:-1]).title()
            url = data.split()[-1]
        else:
            self.__chat_id = data.split()[-1]
            name = f"Чат {self.__chat_id}"
            self.__is_chat = True

        if "Пользователь" in data:
            self.__is_user = True

        elif "Группа" in data:
            self.__is_group = True

        elif "Чат" in data and "https:" in data:
            chat_id, name = map(str.strip, name.split(","))
            self.__chat_id = chat_id.split()[-1]
            self.__is_chat = True

        return dict(zip(("name", "url"), (name, url)))
    
    def __set_period(self, data) -> datetime:
        data = data.replace("в ", '')
        return datetime.datetime.strptime(data, '%d.%m.%Y %H:%M:%S')

    def __set_forward(self, data: list, forwared_message: list) -> None:
        
        if len(forwared_message) != 0:                                                                                              # если имеются пересланые сообщения, то поехали...
            x = 0
            while len(forwared_message) > x:                                                                                        # перебираем полученный список
                if x != len(forwared_message) - 1:
                    start_indx, end_indx = data.index(forwared_message[x]), data.index(forwared_message[x+1])                       # формируем индексы пересланного сообщения
                else:
                    start_indx, end_indx = data.index(forwared_message[x]), len(data) - 1                                           # формируем индексы пересланного сообщения (для последнего)
                    
                self.__message_forward.append(self._select_messages(data[start_indx + 1 : end_indx + 1], self.__suspect_name))      # передаем срез пересланного сообщения в UserCorespondence._select_messages
                del data[start_indx : end_indx]                                                                                     # удаляем срез сформированного пересланного сообщения
                                                                                                                                    # на выходе сохраняем в массив self.__message_forward объект класса Message
                x+=1

            for item in self.__message_forward:
                item._is_forward = True      

    def __set_text(self, data) -> list:
        data = list(map(str.strip, data))

        forwared_message = list(filter(lambda x: "Приклепленно сообщение" in x, data))                          # получаем список элементов с пересланными сообщениями
        self.__set_forward(data, forwared_message)
        
        pin_files = list(filter(lambda x: "Прикрепление" in x, data))                                           # получаем список элементов с прикрепленным (фото, видео, аудио, репосты, стикеры, гифты, файлы)
        for item in pin_files:
            attach_type = item.split()[2]    
                                                                                    
            if attach_type == "photo":                                                                          # если имеются прикрепления photo добавляем в список
                self.__message_photo.append(re.findall("(?<=\()[^()]+(?=\))", item.split()[4])[0])             

            elif attach_type == "link":                                                                         # если имеются прикрепления link добавляем в список
                self.__message_links.append(re.findall("(?<=\()[^()]+(?=,*)|(?=\))", item.split()[-1])[0])

            elif attach_type == "sticker":
                self.__message_sticker = re.findall("(?<=\()[^()]+(?=\))", item.split()[-1])[0]

            elif attach_type == "gift":
                self.__message_gift = re.findall("(?<=\()[^()]+(?=\))", item.split()[-1])[0]

            elif attach_type == "audio":
                self.__message_audio["name"] = " ".join(item.split()[4:])[1:-1]
                self.__message_audio["url"] = item.split()[3]

            elif attach_type == "video":
                self.__message_video.setdefault("name", item.split()[-1][1:-1] if len(item.split()) > 4 else "")
                self.__message_video["url"] = item.split()[3]

            elif attach_type == "wall":                
                self.__message_wall["url"] = item.split()[3]
                self.__message_wall["annotation"] = " ".join(item.split()[4:])[1:-1]

            elif attach_type == "doc":
                if "http" in item and ".ogg" in item:
                    self.__message_voice = re.search("(?<=\()[^()]+(?=\))", item)[0].split()[-1]

                else:
                    name = "".join(item.split()[4:])[1:-1]
                    url = item.split()[3]
                    self.__message_other_files.append((name, url))

            data.remove(item)
        
        if len(data) > 1:
            del data[-1]

        return data

    def __eq__(self, other):
        return self.hash_url == other.hash_url

    def __hash__(self):
        return hash(self.hash_url)

    def __str__(self):
        # return f"{self.__message_recipient} {self.__chat_id}"
        return "recepient: '{name}', message_type: '{type}'\nrelation: 'is_user' - {user}, 'is_group' - {group}, 'is_chat' - {chat}, chat_id - '{chat_id}'\nis_forwared: {forwared}, period: '{period}'\n message_text: {text}\n voice: {voice}\n photo: {photo}\n audio: {audio}\n sticker: {sticker}\n gift: {gift}\n links: {links}\n video: {video}\n wall: {wall}\n forwards_messages: {forwads_messages}\n".format(\
                name=self.__message_recipient["name"], type=self.__message_type, user=self.__is_user, group=self.__is_group, chat=self.__is_chat,\
                forwared=self._is_forward, period=self.__message_period, text=self.__message_text, voice=self.__message_voice, photo=self.__message_photo,\
                audio=self.__message_audio, sticker=self.__message_sticker, gift=self.__message_gift, links=self.__message_links, video=self.__message_video,\
                wall=self.__message_wall, forwads_messages=self.__message_forward, chat_id=self.__chat_id)
    
    @property
    def hash_url(self):
        if self.__is_chat == True:
            return self.__chat_id
            
        return tuple(self.__message_recipient.values())

    @property
    def chat_id(self):
        return self.__chat_id
    
    @property
    def is_chat(self):
        return self.__is_chat

    @property
    def file_path(self):
        if self.__is_chat:
            return f"chat{self.__chat_id}.html"
        else:
            file_name = re.search(r"(?<=vk.com\/)[a-z0-9]+\b", self.user_name["url"], flags=re.I).group()
            return f"{file_name}.html"

    @property
    def user_name(self):
        return self.__message_recipient
    
    @property
    def user_name_main(self):
        if self.__is_chat:
            return dict(zip(("name", "url"), (f"Чат {self.chat_id}", "")))
        else:
            return self.user_name

    @property
    def message_info(self):
        return self.__message_type, self.__message_recipient["name"], self.__message_period.strftime("%d.%m.%Y %H:%M:%S"), self.__suspect_name["name"]
    
    @property
    def text(self):
        return self.__message_text
    
    @property
    def photo(self):
        return self.__message_photo
    
    @property
    def voice(self):
        return self.__message_voice
    
    @property
    def sticker_gift(self):
        return self.__message_sticker if self.__message_sticker else self.__message_gift
    
    @property
    def audio(self):
        return self.__message_audio
    
    @property
    def video(self):
        return self.__message_video
    
    @property
    def wall(self):
        return self.__message_wall
    
    @property
    def other_files(self):
        return self.__message_other_files
    
    @property
    def links(self):
        return self.__message_links
    
    @property
    def forward(self):
        return self.__message_forward