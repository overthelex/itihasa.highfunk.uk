from sources.itihasa import ItihasaHarvester
from sources.dcs import DCSHarvester
from sources.gretil import GretilHarvester
from sources.sarit import SaritHarvester
from sources.suttacentral import SuttaCentralHarvester
from sources.cologne import CologneHarvester
from sources.bdrc import BDRCHarvester
from sources.flores import FloresHarvester
from sources.polyglotta import PolyglottaHarvester
from sources.dsbc import DSBCHarvester
from sources.heritage import HeritageHarvester
from sources.mitra import MitraHarvester
from sources.samayik import SamayikHarvester
from sources.dharmanexus import DharmaNexusHarvester
from sources.leipzig import LeipzigHarvester
from sources.pramana import PramanaHarvester
from sources.ai4bharat import AI4BharatHarvester

ALL_HARVESTERS = [
    # Existing
    ItihasaHarvester,
    DCSHarvester,
    GretilHarvester,
    SaritHarvester,
    SuttaCentralHarvester,
    CologneHarvester,
    BDRCHarvester,
    FloresHarvester,
    PolyglottaHarvester,
    DSBCHarvester,
    HeritageHarvester,
    # New sources
    MitraHarvester,
    SamayikHarvester,
    DharmaNexusHarvester,
    LeipzigHarvester,
    PramanaHarvester,
    AI4BharatHarvester,
]
