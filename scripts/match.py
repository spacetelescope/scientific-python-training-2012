"""simple module to identify matches between two lists

"""

import numpy as np

__author__="P. Greenfield"

def match(list1x, list1y, list2x, list2y, dthreshold):
    """brute force algorithm for matching positions in two lists.
    
    dthreshold is how close to each other items must be to match
    
    This is brute force since each combination of possible positions is checked
    and thus the time goes as the square of the number of positions for a large
    number. There are more complex algorithms that do not have this problem.
    
    """
    x1 = np.array(list1x)
    y1 = np.array(list1y)
    x2 = np.array(list2x)
    y2 = np.array(list2y)
    
    matches = []
    nomatch = []
    for i,x,y in zip(range(len(x1)),x1,y1):
        d = np.sqrt((x-x2)**2+(y-y2)**2)
        closest = np.where(d == d.min())[0][0] # first index is first index array in tuple,
                                               # second is first element of array
        if d[closest] <= dthreshold:
            matches.append((i,closest))
        else:
            nomatch.append((i))
    return matches, nomatch

def filtermags(matches, mags1, mags2, magthreshold):
    """reject matches if magnitudes not similar enough"""
    rejects = []
    for i, (m1, m2) in enumerate(matches):
        print i,m1,m2,mags1[m1],mags1[m2]
        if np.abs(mags1[m1]-mags2[m2]) > magthreshold:
            rejects.append(i)
    # now eliminate rejections from matches, note reverse order!
    print rejects
    rejects.reverse()
    for reject in rejects:
        del matches[reject]
    # why is a return not necessary?
    

