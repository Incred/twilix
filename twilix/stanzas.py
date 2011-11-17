"""
Module discribes stanza-class and basic types of used stanzas. 
There are Message, Presence, Iq classes inherit from Stanza.

Stanzas can be used for incoming stanzas validation and parsing and to
construct your own XML-stanza to be sent into an xmlstream.
"""
from twisted.internet.defer import Deferred
from twisted.words.xish.domish import Element

from twilix.base.velement import VElement
from twilix.base.exceptions import ElementParseError,WrongElement
from twilix.errors import Error
from twilix.htmlim import XHtmlIm
from twilix import fields

class Stanza(VElement):
    """
    Extends VElement class from twilix.base.
    Contains fields corresponding to the protocol.

    Base class for all base XMPP Stanzas (iq, message, presence).
    
    Attributes:
        to -- jid attribue 'to'
        
        from\_  -- jid attribue 'from'
        
        type  -- string attribue 'type'
        
        id  -- string attribue 'id'
        
        lang  -- string attribue 'xml:lang'
        
    """
    elementUri = (
                  'jabber:client',
                  'jabber:server',
                  'jabber:component:accept',
                  None,
                 )

    to = fields.JidAttr('to', required=False)
    from_ = fields.JidAttr('from', required=False)
    type_ = fields.StringAttr('type', required=False)
    id = fields.StringAttr('id', required=False)
    lang = fields.StringAttr('xml:lang', required=False)

    def __init__(self, *args, **kwargs):
        """
        Makes a superclass intialization and set 
        attributes for deferred-style stanzas.
        """
        super(Stanza, self).__init__(*args, **kwargs)
        self.result_class = kwargs.get('result_class', None)
        self.error_class = kwargs.get('error_class', ErrorStanza)

    def __unicode__(self):
        """Overrrides unicode converter."""
        return self.toXml()

    def __repr__(self):
        """Makes avaliable to show stanza in xml format."""
        return self.toXml()

    def makeError(self, content):
        """
        Creates ErrorStanza from self and then returns it.
        Used to make Error Stanza as reply on any Stanza.
        
        :param content: Error element.
        
        :returns: Error Stanza with Error element.
                
        """
        res = ErrorStanza(to=self.from_, from_=self.to, type_='error',
                          el_name=self.elementName, id=self.id,
                          error=content)
        res.children = self.children + res.children
        return res

    def get_reply(self):
        """
        Creates the reply stanza. 
        There is REPLY_CLASS (if defined) or self-type stanza's class.        
        """
        cls = getattr(self, 'REPLY_CLASS', None) or self.__class__
        return cls(to=self.from_, from_=self.to, type_=self.type_, id=self.id)

class ErrorStanza(Stanza):
    """
    Stanza-inheritor class for any errors.
    Contains fields corresponding to the protocol.
    
    Attributes:
        error -- element node with Error element.
        
    """
    error = fields.ElementNode(Error)

class Iq(Stanza):
    """
    Stanza-inheritor class that implements an answer-query type mechanism.
    """
    elementName = 'iq'

    type_ = fields.StringAttr('type')
    id = fields.StringAttr('id')

    def __init__(self, **kwargs):
        """
        Constructor controls for valid value of id,
        calls superclass-constructor and sets deferred 
        attribute for set/get - type queries
        
        """
        if 'id' not in kwargs:
            kwargs['id'] = 'H_%s' % Element._idCounter
            Element._idCounter += 1
        super(Iq, self).__init__(**kwargs)
        if not self.type_ in ('result', 'error') and \
            not kwargs.get('dont_defer', False):
                self.deferred = Deferred()

    def clean_type_(self, value):
        """
        Filters stanzas by type. 
        Used for validation of type\_ field.
        Raises exception for invalid stanzas.
        
        :raises: ElementParseError
        
        """
        if value not in ('set', 'get', 'result', 'error'):
            raise ElementParseError, 'Wrong Iq Type %s' % value
        return value

    def clean_id(self, value):
        """
        Set correct value if id was not found.
        Used for validation of id.    
        """
        if value is None:
            self.addUniqueId()
            return self.id
        return value

    def makeResult(self):
        """Returns result-type Iq stanza"""
        return Iq(to=self.from_, from_=self.to, id=self.id, type_='result',
                  uri=self.uri)

class MyValidator(object):
    """Class for filter stanzas that was sent to myjid."""
    def clean_to(self, v):
        """
        Method raises exception if receiver jid is not host jid.
        
        :raises: WrongElement
        
        """
        if self.host and self.host.dispatcher.myjid != v:
            raise WrongElement
        return v

class MyIq(Iq, MyValidator):
    """Class to filter IQs that was sent to myjid."""
    pass

class Message(Stanza):
    """
    Stanza-inheritor class that implements a message transfer with
    other entities.
    Contains fields corresponding to the protocol.
    
    Attributes:
        body -- string node 'body'
        
        subject  -- string node 'subject'
        
        thread  -- string attribue 'thread'
        
        html  -- element node with XHtmlIm element
        
    """
    elementName = 'message'

    body = fields.StringNode('body', required=False) #?
    subject = fields.StringNode('subject', required=False)
    thread = fields.StringNode('thread', required=False)
    html = fields.ElementNode(XHtmlIm, required=False)

    def clean_type_(self, value):
        """
        Filters stanzas by type. 
        Sets some correct type for invalid stanzas.        
        """
        if not value in ('normal', 'chat', 'groupchat', 'headline', 'error'):
            return 'normal'
        return value

class Presence(Stanza):
    """
    Stanza-inheritor class that implements an entity's presence info.
    Contains fields corresponding to the protocol.
    
    Attributes:
        show -- string node 'show'
        
        status  -- string node 'status'
        
        priority  -- integer attribue 'priority'
                
    """
    elementName = 'presence'

    show = fields.StringNode('show', required=False)
    status = fields.StringNode('status', required=False)
    priority = fields.IntegerNode('priority', required=False)

    def clean_type_(self, value):
        """
        Filters stanzas by type. 
        Sets None type for invalid stanzas.
        
        """
        if not value in ('subscribe', 'subscribed', 'unsubscribe',
                         'unsubscribed', 'available', 'unavailable',
                         'probe', 'error'):
            return None
        return value

    @property
    def type_(self):
        """
        Return type of presence when it's requested. 
        If type is None return 'available'.
        """
        v = self.__getattr__('type_')
        if not v:
            return 'available'
        return v

class Query(VElement):
    """
    VElement-inheritor class. Base for other query-type classes. 
    There is a query part of query-answer mechanism.
    Contains fields corresponding to the protocol.
    
    Attributes:
        node -- string attribute 'node'
        
    """
    elementName = 'query'
    parentClass = Iq

    node = fields.StringAttr('node', required=False)

    def __init__(self, *args, **kwargs):
        """Calls the superclass constructor and sets default value for _iq"""
        self._iq = None
        super(Query, self).__init__(*args, **kwargs)

    @classmethod
    def createFromElement(cls, el, host=None, dont_defer=False):
        """
        Creates new Query element from some element or 
        raises an exception if created failed
        
        :param el: is a source for creating
        
        :param host: host for new element (default None)
        
        :param dont_defer: boolean flag for deferred elements
        
        :raises: WrongElement
        
        :returns: new element creating from source
        
        """
        parent = cls.parentClass.createFromElement(el, host=host,
                                                   dont_defer=dont_defer)
        el = parent.firstChildElement()
        if el is None:
            raise WrongElement
        if el.uri != cls.elementUri or el.name != cls.elementName:
            raise WrongElement
        query = super(Query, cls).createFromElement(el, host=host)
        query.parent = parent
        query.children = el.children
        return query

    @property
    def iq(self):
        """Return valid iq when it's requested."""
        if self._iq is None:
            self._iq = self.topElement()
        return self._iq
