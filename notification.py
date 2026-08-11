from abc import ABC, abstractmethod
from typing import List

class INotification(ABC):
  @abstractmethod
  def getcontent(self) -> str:
    pass

class SimpleNotification(INotification):
    def __init__(self, msg:str):
        self._msg = msg
    def getcontent(self)-> str:
        return self._msg

class INotificationDecorator(INotification,ABC):
    def __init__(self, notification:INotification):
        self._notification = notification

class TimeStampDecorator(INotificationDecorator):
    def getcontent(self)->str:
        return f"time {self._notification.getcontent()}"
class SignatureDecorator(INotificationDecorator):
    def __init__(self, n:INotification, sign):
        super().__init__(n)
        self._sign = sign
    def getcontent(self)->str:
        return f"{self._sign} {self._notification.getcontent()}"      

class IObserver(ABC):
    @abstractmethod
    def update(self)->None:
        pass

class IObservable(ABC):
    @abstractmethod
    def addObserver(self, observer: IObserver)->None:
        pass 
    @abstractmethod
    def removeObserver(self, observer: IObserver)->None:
        pass 
    @abstractmethod
    def notify_observers(self)->None:
        pass   

class NotificationObservable(IObservable):
    
    def __init__(self):
        self._observers: List[IObserver] = []
        self._current_notification: INotification =  None

    def addObserver(self, obs:IObserver)-> None:
        self._observers.append(obs) 

    def removeObserver(self, obs: IObserver)-> None:
        self._observers.remove(obs)  

    def notify_observers(self)->None:
        for ob in self._observers:
            ob.update()
    def setNotification(self, notification:INotification)->None:
        self._current_notification = notification
        self.notify_observers()

    def getNotification(self)->INotification:
        return self._current_notification 
    def getNotificationContent(self)->INotification:
        return self._current_notification.getcontent()

class Logger(IObserver):
    def __init__(self, notifObservable: IObservable)->None:
        self._observable = notifObservable

    def update(self):
        content = self._observable.getNotificationContent()
        print(f"logger {content}")


class INotificationStrategy(ABC):
    @abstractmethod
    def send_notification(self, content:str)->None:
        pass

class EmailStrategy(INotificationStrategy):
     
     def __init__(self, email:str):
         self._email = email
     def send_notification(self, content:str)->None:
        print(f"email {self._email} {content}")


class SmsStrategy(INotificationStrategy):
     
     def __init__(self, number):
         self._number = number
     def send_notification(self, content:str)->None:
        print(f"SMS {self._number} {content}")

class PopUpStrategy(INotificationStrategy):
     
    def send_notification(self, content:str)->None:
        print(f"pop  {content}") 

class NotificationEngine(IObserver):
      def __init__(self, notif_observable:IObservable):
        self._notif_observable = notif_observable
        self._notif_stratgies:List[INotificationStrategy] = []

      def addStrategy(self, strategy:INotificationStrategy)-> None:
        self._notif_stratgies.append(strategy)   
        
      def update(self)->None:
        content  = self._notif_observable.getNotificationContent()
        for s in self._notif_stratgies:
            s.send_notification(content) 


class NotificationService():
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
            cls._instance._observable = NotificationObservable()
            cls._instance._notifications: List[INotification] = []
            return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def get_observable(self):
        return self._observable       

    def send_notification(self, notification:INotification):
        self._notifications.append(notification)
        self._observable.setNotification(notification)    


if __name__ == "__main__":
    notification_service = NotificationService.get_instance()  
    notification_observable = notification_service.get_observable()

    logger = Logger(notification_observable)
    notif_engine = NotificationEngine(notification_observable)    
    notif_engine.addStrategy(SmsStrategy(334))     
    notif_engine.addStrategy(EmailStrategy("wde"))     
    notif_engine.addStrategy(PopUpStrategy()) 

    notification_observable.addObserver(logger)
    notification_observable.addObserver(notif_engine)

    notif = SimpleNotification("testing")
    notif = TimeStampDecorator(notif)
    notif = SignatureDecorator(notif,"JS")

    notification_service.send_notification(notif)









