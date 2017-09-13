
# BlueskyMagics were imported and registered in 00-startup.py

BlueskyMagics.detectors = [pilatus2M]
BlueskyMagics.positioners = [smx,smy,sth,schi,sphi,srot,strans,strans2,stilt,stilt2, DETx,DETy,WAXSx,SAXSx,SAXSy, bsx,bsy,bsphi, camx,camy, armz,armx,armphi,army,armr, bim3y,fs3y,bim4y,bim5y, s0.tp, s0.bt, s0.ob, s0.ib, s0.xc, s0.yc, s0.xg, s0.yg, s1.xc, s1.yc, s1.xg, s1.yg, s2.xc, s2.yc, s2.xg, s2.yg, s3.xc, s3.yc, s3.xg, s3.yg, s4.xc, s4.yc, s4.xg, s4.yg, s5.xc, s5.yc, s5.xg, s5.yg, mono_bragg,mono_pitch2,mono_roll2,mono_perp2, mir_usx,mir_dsx,mir_usy,mir_dsyi,mir_dsyo,mir_bend]

### Override the %wa magic with one that includes offsets.
### Later this will be added to bluesky itself and will not
### need to be customized here.


from IPython.core.magic import Magics, magics_class, line_magic
from operator import attrgetter


@magics_class
class CMSCustomMagics(BlueskyMagics):
    @line_magic
    def wa(self, line):
        "List positioner info. 'wa' stands for 'where all'."
        if line.strip():
            positioners = eval(line, self.shell.user_ns)
        else:
            positioners = self.positioners
        positioners = sorted(set(positioners), key=attrgetter('name'))
        values = []
        for p in positioners:
            try:
                values.append(p.position)
            except Exception as exc:
                values.append(exc)

        headers = ['Positioner', 'Value', 'Low Limit', 'High Limit', 'Offset']
        LINE_FMT = '{: <30} {: <10} {: <10} {: <10} {: <10}'
        lines = []
        lines.append(LINE_FMT.format(*headers))
        for p, v in zip(positioners, values):
            if not isinstance(v, Exception):
                try:
                    prec = p.precision
                except Exception:
                    prec = self.FMT_PREC
                value = np.round(v, decimals=prec)
                try:
                    low_limit, high_limit = p.limits
                except Exception as exc:
                    low_limit = high_limit = exc.__class__.__name__
                else:
                    low_limit = np.round(low_limit, decimals=prec)
                    high_limit = np.round(high_limit, decimals=prec)
                try:
                    offset = p.user_offset.get()
                except Exception as exc:
                    offset = exc.__class__.__name__
                else:
                    offset = np.round(offset, decimals=prec)
            else:
                value = v.__class__.__name__  # e.g. 'DisconnectedError'
                low_limit = high_limit = ''

            lines.append(LINE_FMT.format(p.name, value, low_limit, high_limit,
                                         offset))
        print('\n'.join(lines))

# This will override the %wa registered from BlueskyMagics
get_ipython().register_magics(CMSCustomMagics)
