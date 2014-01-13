import inspect

def validate_int(var):
    if var is None:
        raise UnboundLocalError('var is None')
    elif not isinstance(var, int):
        raise TypeError('var is not an int')


def validate_user_method(var):
    if var is None:
        raise UnboundLocalError('method variable is None')
    elif not inspect.ismethod(var):
        raise TypeError('method variable not a reference to a method')

def validate_string(var):
    if var is None:
        raise UnboundLocalError('var is None')
    elif not isinstance(var, basestring):
        raise TypeError('var is not a basestring')
    elif len(var) == 0:
        raise ValueError('var is a 0-length string')

def validate_dict(var):
    if var is None:
        raise UnboundLocalError('var is None')
    elif not isinstance(var, dict):
        raise TypeError('var is not a dict')

def validate_dict_nonempty(var):
    validate_dict(var)
    if len(var) == 0:
        raise ValueError('var is an empty dict')
    
def validate_object(var):
    if var is None:
        raise UnboundLocalError('var is None')


