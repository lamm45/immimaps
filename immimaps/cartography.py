"""Functions for plotting colored maps

A simple demo map can be drawn by running this file as a module with
`python -m immimaps.cartography`
"""

import cartopy.crs as ccrs
import cartopy.io.shapereader as shapereader

import matplotlib.colors
import matplotlib.cm
import matplotlib.patches
import matplotlib.pyplot as plt

from . import geography


def _get_reader(location):
    """Get shapereader"""
    if location == 'us':
        shapefile = shapereader.natural_earth(
            resolution='110m',
            category='cultural',
            name='admin_1_states_provinces_lakes'
        )
    elif location == 'world':
        shapefile = shapereader.natural_earth(
            resolution='110m',
            category='cultural',
            name='admin_0_countries'
        )
    else:
        raise RuntimeError('Unknown georeader location.')

    reader = shapereader.Reader(shapefile)
    return reader


def _add_inset(ax, axpos, record, color=(1, 1, 1), projection=ccrs.Mercator()):
    """Create an inset map with and draw geometry in it"""
    inset = ax.inset_axes(axpos, projection=projection)
    inset.add_geometries([record.geometry], ccrs.PlateCarree(),
                         edgecolor='black', facecolor=color)
    b = record.bounds
    inset.set_extent((b[0], b[2], b[1], b[3]))
    inset.set_frame_on(False)
    return inset


def _add_tiny(ax, datapos, radius, color=(1, 1, 1)):
    """Draw filled circle"""
    marker = matplotlib.patches.Circle(xy=datapos, radius=radius, edgecolor='black',
                                       facecolor=color, zorder=4.9)
    ax.add_patch(marker)
    return marker


def draw_us_map(statevals=None, *, fig=None,
                defaultval=None, defaultcolor=None,
                clim=None, cmap=None):
    """Draw colored U.S. map using numerical value for each state"""
    if statevals is None:
        statevals = dict()
    if fig is None:
        fig = plt.figure()

    map_extent_degrees = (-125, -65, 20, 50)
    alaska_extent_axes = (0.08, 0.1, 0.22, 0.22)
    hawaii_extent_axes = (0.25, 0.15, 0.1, 0.1)
    puerto_rico_extent_axes = (0.55, 0.13, 0.03, 0.03)
    tiny_radius_meters = 22000
    tiny_margin_axes = 0.03

    ax = fig.add_subplot(projection=ccrs.LambertConformal())
    ax.set_extent(map_extent_degrees)

    # Define colors
    minval = clim[0] if clim is not None else min(statevals.values())
    maxval = clim[1] if clim is not None else max(statevals.values())
    norm = matplotlib.colors.Normalize(minval, maxval)
    sm = matplotlib.cm.ScalarMappable(norm, cmap)
    if defaultcolor is None:
        if defaultval is None:
            defaultval = 0.0
        defaultcolor = sm.to_rgba(defaultval)
    def abbrv_to_color(abbrv):
        return sm.to_rgba(statevals[abbrv]) if abbrv in statevals else defaultcolor

    # Add 50 states and D.C.
    reader = _get_reader('us')
    for state in reader.records():
        abbrv = state.attributes['postal']
        color = abbrv_to_color(abbrv)
        if abbrv == 'AK':
            _add_inset(ax, alaska_extent_axes, state, color)
        if abbrv == 'DC':
            lon = state.attributes['longitude']
            lat = state.attributes['latitude']
            pos = ccrs.LambertConformal().transform_point(lon, lat, ccrs.PlateCarree())
            _add_tiny(ax, pos, tiny_radius_meters, color)
        if abbrv == 'HI':
            _add_inset(ax, hawaii_extent_axes, state, color)
        else:
            ax.add_geometries([state.geometry], ccrs.PlateCarree(),
                              edgecolor='none', facecolor=color)

    # Draw all boundaries at the same time for better quality
    ax.add_geometries(reader.geometries(), ccrs.PlateCarree(),
                      edgecolor='black', facecolor=(0, 0, 0, 0))

    # Add Puerto Rico
    reader = _get_reader('world')
    for country in reader.records():
        if country.attributes['NAME'] =='Puerto Rico':
            color = abbrv_to_color('PR')
            _add_inset(ax, puerto_rico_extent_axes, country, color)
            break

    # Add remaining territories
    territories = ('AS', 'GU', 'MP', 'VI')
    x0 = puerto_rico_extent_axes[0] + 0.5*puerto_rico_extent_axes[2] - \
        0.5*(len(territories)-1)*tiny_margin_axes
    y0 = puerto_rico_extent_axes[1] - tiny_margin_axes
    for terr in territories:
        datapos = ax.transData.inverted().transform(ax.transAxes.transform((x0, y0)))
        x0 += tiny_margin_axes
        color = abbrv_to_color(terr)
        _add_tiny(ax, datapos, tiny_radius_meters, color)
        ax.text(datapos[0], datapos[1]-tiny_radius_meters*1.5, terr, ha='center', va='top')

    return ax, sm


def demo():
    """Draw an example U.S. map where the coloring is based on the name of the state"""

    # Assign numerical value for each state based on the first letter of the name
    states = geography.us_states()
    for abbrv, name in states.items():
        states[abbrv] = ord(name[0]) - ord('A')

    # Draw map
    ax, sm = draw_us_map(states, clim=(0, ord('Z')-ord('A')), cmap='coolwarm')

    # Customize figure
    plt.title('First letter of the state name')
    plt.colorbar(sm, ax=ax)
    plt.tight_layout()

    # Show figure
    plt.show()


if __name__ == '__main__':
    demo()
