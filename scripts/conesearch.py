# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Common utilities for accessing VO simple services.

"""
from __future__ import print_function, division

# STDLIB
import json
import urllib

# ASTROPY

from astropy.io.votable import table
from astropy.io.votable.exceptions import vo_raise, vo_warn, E19, W24, W25
from astropy.utils.console import color_print
from astropy.utils.data import get_readable_fileobj

VO_PEDANTIC = table.PEDANTIC()


class VOSError(Exception):  # pragma: no cover
    pass

def vo_service_request(url,  **kwargs):
    if len(kwargs) and not (url.endswith('?') or url.endswith('&')):
        raise VOSError("url should already end with '?' or '&'")

    query = []
    for key, value in kwargs.iteritems():
        query.append('{}={}'.format(
            urllib.quote(key), urllib.quote_plus(str(value))))

    parsed_url = url + '&'.join(query)
    with get_readable_fileobj(parsed_url) as req:
        tab = table.parse(req, filename=parsed_url, pedantic=False)
        #outfile = open('test.dat','wb')
        #outfile.write(req.read())
        #outfile.close()
    return vo_tab_parse(tab, url, kwargs)

def vo_tab_parse(tab, url, kwargs):
    """
    In case of errors from the server, a complete and correct
    'stub' VOTable file may still be returned.  This is to
    detect that case.

    Parameters
    ----------
    tab : `astropy.io.votable.tree.VOTableFile` object

    url : string
        URL used to obtain `tab`.

    kwargs : dict
        Keywords used to obtain `tab`, if any.

    Returns
    -------
    out_tab : `astropy.io.votable.tree.Table` object

    Raises
    ------
    IndexError
        Table iterator fails.

    VOSError
        Server returns error message or invalid table.

    """
    for param in tab.iter_fields_and_params():
        if param.ID.lower() == 'error':
            raise VOSError("Catalog server '{0}' returned error '{1}'".format(
                url, param.value))
        break

    if tab.resources == []:
        vo_raise(E19)

    for info in tab.resources[0].infos:
        if info.name == 'QUERY_STATUS' and info.value != 'OK':
            if info.content is not None:
                long_descr = ':\n{0}'.format(info.content)
            else:
                long_descr = ''
            raise VOSError("Catalog server '{0}' returned status "
                           "'{1}'{2}".format(url, info.value, long_descr))
        break

    out_tab = tab.get_first_table()

    kw_sr = [k for k in kwargs if 'sr' == k.lower()]
    if len(kw_sr) == 0:
        sr = 0
    else:
        sr = kwargs.get(kw_sr[0])

    if sr != 0 and out_tab.array.size <= 0:
        raise VOSError("Catalog server '{0}' returned {1} result".format(
            url, out_tab.array.size))

    out_tab.url = url  # Track the URL
    return out_tab