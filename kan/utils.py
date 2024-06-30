import warnings

import numpy as np
import torch
from sklearn.linear_model import LinearRegression
import sympy

from kan import KAN


# name: (torch implementation, sympy implementation)
# SYMBOLIC_LIB = {'x': (lambda x: x, lambda x: x),
#                  'x^2': (lambda x: x**2, lambda x: x**2),
#                  'x^3': (lambda x: x**3, lambda x: x**3),
#                  'x^4': (lambda x: x**4, lambda x: x**4),
#                  '1/x': (lambda x: 1/x, lambda x: 1/x),
#                  '1/x^2': (lambda x: 1/x**2, lambda x: 1/x**2),
#                  '1/x^3': (lambda x: 1/x**3, lambda x: 1/x**3),
#                  '1/x^4': (lambda x: 1/x**4, lambda x: 1/x**4),
#                  'sqrt': (lambda x: torch.sqrt(x), lambda x: sympy.sqrt(x)),
#                  '1/sqrt(x)': (lambda x: 1/torch.sqrt(x), lambda x: 1/sympy.sqrt(x)),
#                  'exp': (lambda x: torch.exp(x), lambda x: sympy.exp(x)),
#                  'log': (lambda x: torch.log(x), lambda x: sympy.log(x)),
#                  'abs': (lambda x: torch.abs(x), lambda x: sympy.Abs(x)),
#                  'sin': (lambda x: torch.sin(x), lambda x: sympy.sin(x)),
#                  'tan': (lambda x: torch.tan(x), lambda x: sympy.tan(x)),
#                  'tanh': (lambda x: torch.tanh(x), lambda x: sympy.tanh(x)),
#                  'sigmoid': (lambda x: torch.sigmoid(x), sympy.Function('sigmoid')),
#                  #'relu': (lambda x: torch.relu(x), relu),
#                  'sgn': (lambda x: torch.sign(x), lambda x: sympy.sign(x)),
#                  'arcsin': (lambda x: torch.arcsin(x), lambda x: sympy.arcsin(x)),
#                  'arctan': (lambda x: torch.arctan(x), lambda x: sympy.atan(x)),
#                  'arctanh': (lambda x: torch.arctanh(x), lambda x: sympy.atanh(x)),
#                  '0': (lambda x: x*0, lambda x: x*0),
#                  'gaussian': (lambda x: torch.exp(-x**2), lambda x: sympy.exp(-x**2)),
#                  'cosh': (lambda x: torch.cosh(x), lambda x: sympy.cosh(x)),
#                  #'logcosh': (lambda x: torch.log(torch.cosh(x)), lambda x: sympy.log(sympy.cosh(x))),
#                  #'cosh^2': (lambda x: torch.cosh(x)**2, lambda x: sympy.cosh(x)**2),
# }


def safe_inverse(x, eps0=1e-8, eps1=1e-16):
    return 1 / (x + torch.sign(x + eps0) * eps1)


def safe_inverse_sympy(x, eps0=1e-8, eps1=1e-16):
    return 1 / (x + sympy.sign(x + eps0) * eps1)


def safe_exp(x, clip_value=20):
    return torch.exp(torch.clamp(x, min=-clip_value, max=clip_value))


def safe_exp_sympy(x, clip_value=20):
    return sympy.exp(sympy.Max(sympy.Min(x, clip_value), -clip_value))


def safe_log(x, epsilon=1e-8):
    return torch.log(torch.clamp(x, min=epsilon))


def safe_log_sympy(x, epsilon=1e-8):
    return sympy.log(sympy.Max(x, epsilon))


def safe_sqrt(x):
    return torch.sqrt(torch.relu(x))


def safe_sqrt_sympy(x):
    return sympy.sqrt(sympy.Max(x, 0))


def safe_tan(x, epsilon=1e-6):
    pi_half = torch.tensor(torch.pi / 2)
    return torch.tan(torch.clamp(x, min=-pi_half + epsilon, max=pi_half - epsilon))


def safe_tan_sympy(x, epsilon=1e-6):
    pi_half = sympy.pi / 2
    return sympy.tan(sympy.Min(sympy.Max(x, -pi_half + epsilon), pi_half - epsilon))


def safe_arcsin(x, epsilon=1e-6):
    return torch.asin(torch.clamp(x, min=-1 + epsilon, max=1 - epsilon))


def safe_arcsin_sympy(x, epsilon=1e-6):
    return sympy.asin(sympy.Min(sympy.Max(x, -1 + epsilon), 1 - epsilon))


def elu(x, alpha=1.0):
    return torch.where(x > 0, x, alpha * (torch.exp(x) - 1))


def elu_sympy(x, alpha=1.0):
    return sympy.Piecewise((x, x > 0), (alpha * (sympy.exp(x) - 1), True))


def softplus(x):
    return torch.log1p(torch.exp(-torch.abs(x))) + torch.relu(x)


def softplus_sympy(x):
    return sympy.log(1 + sympy.exp(-sympy.Abs(x))) + sympy.Max(x, 0)


SYMBOLIC_LIB = {
    '0': (lambda x: x * 0, lambda x: x * 0),
    'x': (lambda x: x, lambda x: x),
    'x^2': (lambda x: x ** 2, lambda x: x ** 2),
    'x^3': (lambda x: x ** 3, lambda x: x ** 3),
    'x^4': (lambda x: x ** 4, lambda x: x ** 4),
    'x^5': (lambda x: x ** 5, lambda x: x ** 5),
    'abs': (lambda x: torch.abs(x), lambda x: sympy.Abs(x)),
    'sgn': (lambda x: torch.sign(x), lambda x: sympy.sign(x)),
    'sin': (lambda x: torch.sin(x), lambda x: sympy.sin(x)),
    'arctan': (lambda x: torch.arctan(x), lambda x: sympy.atan(x)),
    'tanh': (lambda x: torch.tanh(x), lambda x: sympy.tanh(x)),
    'cosh': (lambda x: torch.cosh(x), lambda x: sympy.cosh(x)),
    'cosh^2': (lambda x: torch.cosh(x)**2, lambda x: sympy.cosh(x)**2),
    'sigmoid': (lambda x: torch.sigmoid(x), sympy.Function('sigmoid')),
    'relu': (lambda x: torch.relu(x), lambda x: sympy.Max(x, 0)),
    'elu': (lambda x: elu(x), lambda x: elu_sympy(x)),
    'softplus': (lambda x: softplus(x), lambda x: softplus_sympy(x)),
    'gaussian': (lambda x: torch.exp(-x ** 2), lambda x: sympy.exp(-x ** 2)),

    # Risky functions with safety measures:
    '1/x': (lambda x: safe_inverse(x), lambda x: safe_inverse_sympy(x)),
    '1/x^2': (lambda x: safe_inverse(x ** 2), lambda x: safe_inverse_sympy(x ** 2)),
    '1/x^3': (lambda x: safe_inverse(x ** 3), lambda x: safe_inverse_sympy(x ** 3)),
    '1/x^4': (lambda x: safe_inverse(x ** 4), lambda x: safe_inverse_sympy(x ** 4)),
    'sqrt': (lambda x: safe_sqrt(x), lambda x: safe_sqrt_sympy(x)),
    '1/sqrt(x)': (lambda x: safe_inverse(safe_sqrt(x)), lambda x: safe_inverse_sympy(safe_sqrt_sympy(x))),
    'exp': (lambda x: safe_exp(x), lambda x: safe_exp_sympy(x)),
    'log': (lambda x: safe_log(x), lambda x: safe_log_sympy(x)),
    'logcosh': (lambda x: safe_log(torch.cosh(x)), lambda x: safe_log_sympy(sympy.cosh(x))),
    'tan': (lambda x: safe_tan(x), lambda x: safe_tan_sympy(x)),
    'arcsin': (lambda x: safe_arcsin(x), lambda x: safe_arcsin_sympy(x)),
}


def create_dataset(f, 
                   n_var=2, 
                   ranges = [-1,1],
                   train_num=1000, 
                   test_num=1000,
                   normalize_input=False,
                   normalize_label=False,
                   device='cpu',
                   seed=0):
    '''
    create dataset
    
    Args:
    -----
        f : function
            the symbolic formula used to create the synthetic dataset
        ranges : list or np.array; shape (2,) or (n_var, 2)
            the range of input variables. Default: [-1,1].
        train_num : int
            the number of training samples. Default: 1000.
        test_num : int
            the number of test samples. Default: 1000.
        normalize_input : bool
            If True, apply normalization to inputs. Default: False.
        normalize_label : bool
            If True, apply normalization to labels. Default: False.
        device : str
            device. Default: 'cpu'.
        seed : int
            random seed. Default: 0.
        
    Returns:
    --------
        dataset : dic
            Train/test inputs/labels are dataset['train_input'], dataset['train_label'],
                        dataset['test_input'], dataset['test_label']
         
    Example
    -------
    >>> f = lambda x: torch.exp(torch.sin(torch.pi*x[:,[0]]) + x[:,[1]]**2)
    >>> dataset = create_dataset(f, n_var=2, train_num=100)
    >>> dataset['train_input'].shape
    torch.Size([100, 2])
    '''

    np.random.seed(seed)
    torch.manual_seed(seed)

    if len(np.array(ranges).shape) == 1:
        ranges = np.array(ranges * n_var).reshape(n_var,2)
    else:
        ranges = np.array(ranges)
        
    train_input = torch.zeros(train_num, n_var)
    test_input = torch.zeros(test_num, n_var)
    for i in range(n_var):
        train_input[:,i] = torch.rand(train_num,)*(ranges[i,1]-ranges[i,0])+ranges[i,0]
        test_input[:,i] = torch.rand(test_num,)*(ranges[i,1]-ranges[i,0])+ranges[i,0]
        
        
    train_label = f(train_input)
    test_label = f(test_input)
        
        
    def normalize(data, mean, std):
            return (data-mean)/std
            
    if normalize_input == True:
        mean_input = torch.mean(train_input, dim=0, keepdim=True)
        std_input = torch.std(train_input, dim=0, keepdim=True)
        train_input = normalize(train_input, mean_input, std_input)
        test_input = normalize(test_input, mean_input, std_input)
        
    if normalize_label == True:
        mean_label = torch.mean(train_label, dim=0, keepdim=True)
        std_label = torch.std(train_label, dim=0, keepdim=True)
        train_label = normalize(train_label, mean_label, std_label)
        test_label = normalize(test_label, mean_label, std_label)

    dataset = {}
    dataset['train_input'] = train_input.to(device)
    dataset['test_input'] = test_input.to(device)

    dataset['train_label'] = train_label.to(device)
    dataset['test_label'] = test_label.to(device)

    return dataset



def fit_params(x, y, fun, a_range=(-10,10), b_range=(-10,10), grid_number=101, iteration=3, verbose=True, device='cpu'):
    '''
    fit a, b, c, d such that
    
    .. math::
        |y-(cf(ax+b)+d)|^2
        
    is minimized. Both x and y are 1D array. Sweep a and b, find the best fitted model.
    
    Args:
    -----
        x : 1D array
            x values
        y : 1D array
            y values
        fun : function
            symbolic function
        a_range : tuple
            sweeping range of a
        b_range : tuple
            sweeping range of b
        grid_num : int
            number of steps along a and b
        iteration : int
            number of zooming in
        verbose : bool
            print extra information if True
        device : str
            device
        
    Returns:
    --------
        a_best : float
            best fitted a
        b_best : float
            best fitted b
        c_best : float
            best fitted c
        d_best : float
            best fitted d
        r2_best : float
            best r2 (coefficient of determination)
    
    Example
    -------
    >>> num = 100
    >>> x = torch.linspace(-1,1,steps=num)
    >>> noises = torch.normal(0,1,(num,)) * 0.02
    >>> y = 5.0*torch.sin(3.0*x + 2.0) + 0.7 + noises
    >>> fit_params(x, y, torch.sin)
    r2 is 0.9999727010726929
    (tensor([2.9982, 1.9996, 5.0053, 0.7011]), tensor(1.0000))
    '''
    # fit a, b, c, d such that y=c*fun(a*x+b)+d; both x and y are 1D array.
    # sweep a and b, choose the best fitted model   
    for _ in range(iteration):
        a_ = torch.linspace(a_range[0], a_range[1], steps=grid_number, device=device)
        b_ = torch.linspace(b_range[0], b_range[1], steps=grid_number, device=device)
        a_grid, b_grid = torch.meshgrid(a_, b_, indexing='ij')
        post_fun = fun(a_grid[None,:,:] * x[:,None,None] + b_grid[None,:,:])
        x_mean = torch.mean(post_fun, dim=[0], keepdim=True)
        y_mean = torch.mean(y, dim=[0], keepdim=True)
        numerator = torch.sum((post_fun - x_mean)*(y-y_mean)[:,None,None], dim=0)**2
        denominator = torch.sum((post_fun - x_mean)**2, dim=0)*torch.sum((y - y_mean)[:,None,None]**2, dim=0)
        r2 = numerator/(denominator+1e-4)
        r2 = torch.nan_to_num(r2)
        
        
        best_id = torch.argmax(r2)
        a_id, b_id = torch.div(best_id, grid_number, rounding_mode='floor'), best_id % grid_number
        
        
        if a_id == 0 or a_id == grid_number - 1 or b_id == 0 or b_id == grid_number - 1:
            if _ == 0 and verbose==True:
                print('Best value at boundary.')
            if a_id == 0:
                a_range = [a_[0], a_[1]]
            if a_id == grid_number - 1:
                a_range = [a_[-2], a_[-1]]
            if b_id == 0:
                b_range = [b_[0], b_[1]]
            if b_id == grid_number - 1:
                b_range = [b_[-2], b_[-1]]
            
        else:
            a_range = [a_[a_id-1], a_[a_id+1]]
            b_range = [b_[b_id-1], b_[b_id+1]]
            
    a_best = a_[a_id]
    b_best = b_[b_id]
    post_fun = fun(a_best * x + b_best)
    r2_best = r2[a_id, b_id]
    
    if verbose == True:
        print(f"r2 is {r2_best}")
        if r2_best < 0.9:
            print(f'r2 is not very high, please double check if you are choosing the correct symbolic function.')

    post_fun = torch.nan_to_num(post_fun)
    reg = LinearRegression().fit(post_fun[:,None].detach().cpu().numpy(), y.detach().cpu().numpy())
    c_best = torch.from_numpy(reg.coef_)[0].to(device)
    d_best = torch.from_numpy(np.array(reg.intercept_)).to(device)
    return torch.stack([a_best, b_best, c_best, d_best]), r2_best


def add_symbolic(name, fun):
    '''
    add a symbolic function to library
    
    Args:
    -----
        name : str
            name of the function
        fun : fun
            torch function or lambda function
    
    Returns:
    --------
        None
    
    Example
    -------
    >>> print(SYMBOLIC_LIB['Bessel'])
    KeyError: 'Bessel'
    >>> add_symbolic('Bessel', torch.special.bessel_j0)
    >>> print(SYMBOLIC_LIB['Bessel'])
    (<built-in function special_bessel_j0>, Bessel)
    '''
    exec(f"globals()['{name}'] = sympy.Function('{name}')")
    SYMBOLIC_LIB[name] = (fun, globals()[name])


def autosym_model(model: KAN, skip_first_layer=True, r2_threshold=0.99, r2_diff_threshold=0.01, **tdqm_kwargs):
    width = model.width
    for l in range(skip_first_layer, len(width) - 1):
        for i in range(width[l]):
            for j in range(width[l + 1]):
                # if model.symbolic_fun[l].mask[j, i] > 0.0:
                #     continue
                str_edge = f"Layer {l}, Node {i} -> Layer {l + 1}, Node {j}"
                try:
                    warnings.filterwarnings("ignore")
                    fun, _, r2, second_best_r2 = model.suggest_symbolic(l, i, j, lib=SYMBOLIC_LIB, verbose=False)
                    warnings.filterwarnings("default")
                except ValueError as e:
                    print(f"{str_edge}: {e}")
                    continue
                if r2 > r2_threshold and r2 - second_best_r2 > r2_diff_threshold:
                    print(f"{str_edge}: {fun}")
                    model.fix_symbolic(l, i, j, fun)
                # else:
                #     print(f"{str_edge}: No symbolic found.")
    # process_map(partial(autosym_edge, model, r2_threshold), edges, **tdqm_kwargs)
