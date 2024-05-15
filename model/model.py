class User:
    def __init__(self, _id, user_name, password, phone_number,basari_puani,user_type,kayit_tarihi,token,level,name):
        self._id = _id
        self.user_name = user_name
        self.password = password
        self.phone_number = phone_number
        self.basari_puani = basari_puani
        self.tamamlanan_gun = 0
        self.user_type = user_type
        self.kayit_tarihi = kayit_tarihi
        self.token = token
        self.level = level
        self.user_type =user_type
        self.name = name
        
        
             
class Egzersiz:
    def __init__(self, _id, name, text, egzersiz_puanı, egzersiz_seviyesi):
        self._id = _id
        self.name = name
        self.text = text
        self.egzersiz_puanı = egzersiz_puanı
        self.egzersiz_seviyesi = egzersiz_seviyesi

    # Getter ve Setter metotları
    def get_id(self):
        return self._id
    
    def set_id(self, _id):
        self._id = _id
    
    def get_name(self):
        return self.name
    
    def set_name(self, name):
        self.name = name
    
    def get_text(self):
        return self.text
    
    def set_text(self, text):
        self.text = text
    
    def get_egzersiz_puani(self):
        return self.egzersiz_puani
    
    def set_egzersiz_puani(self, egzersiz_puani):
        self.egzersiz_puani = egzersiz_puani
    
    def get_egzersiz_seviyesi(self):
        return self.egzersiz_seviyesi
    
    def set_egzersiz_seviyesi(self, egzersiz_seviyesi):
        self.egzersiz_seviyesi = egzersiz_seviyesi
          
class Story:
    def __init__(self,_id,text,seviye) :
        self._id = _id
        self.text =text
        self.seviye = seviye
    
    def get_metin_seviyesi(self):
        return self.egzersiz_seviyesi
    
    def set_metin_seviyesi(self, egzersiz_seviyesi):
        self.egzersiz_seviyesi = egzersiz_seviyesi
      
    def get_text(self):
        return self.text
    
    def set_text(self, text):
        self.text = text
    
    
    
class Video:
    def __init__(self,video_name,video_url,description):
        self.video_name = video_name
        self.description = description
        self.video_url = video_url



class Messages:
    def __init__(self,header, sender, receiver, date,cender_date,content):
        self.sender = sender
        self.header = header
        self.receiver = receiver
        self.date = date
        self.content = content

class Task:
    def __init__(self,date, who,content,id):
        self.who = who
        self.date = date
        self.content = content
        self.task_id = id



class Process:
    def __init__(self,user_name,next_exercise,now_exercise,day,next_day_date,okey):
        self.user_name = user_name
        self.next_exercise = next_exercise
        self.now_exercise= now_exercise
        self.day = day
        self.next_day_date = next_day_date
        self.okey = okey