import logging

from ableton.v3.base import listens
from ableton.v3.control_surface import (
    ControlSurface,
    ControlSurfaceSpecification,
    ElementsBase,
    MapMode,
    Skin,
)
from ableton.v3.control_surface.elements import SimpleColor
from ableton.v3.control_surface.mode import ModesComponent

logger = logging.getLogger(__name__)

def log(msg):
    logger.info(f"MGTwister2: {msg}")

class RGB(object):
    OFF = SimpleColor(0)

    DARK_BLUE = SimpleColor(1)
    LIGHT_BLUE = SimpleColor(25)
    TURQUOISE = SimpleColor(37)
    GREEN = SimpleColor(43)
    YELLOW = SimpleColor(61)
    ORANGE = SimpleColor(69)
    RED = SimpleColor(78)
    PINK = SimpleColor(97)
    PURPLE = SimpleColor(113)
    AQUA = SimpleColor(127)


class Colors(object):
    class DefaultButton(object):
        On = RGB.TURQUOISE
        Off = RGB.OFF
        Disabled = RGB.OFF

    class Mixer(object):
        MuteOn = RGB.ORANGE
        MuteOff = RGB.OFF
        ArmOn = RGB.RED
        ArmOff = RGB.OFF
        SoloOn = RGB.DARK_BLUE
        SoloOff = RGB.OFF
        Selected = RGB.RED
        NotSelected = RGB.ORANGE
        NoTrack = RGB.OFF

    class Session(object):
        Navigation = RGB.DARK_BLUE
        NavigationPressed = RGB.LIGHT_BLUE

    class Device(object):
        Navigation = RGB.LIGHT_BLUE
        NavigationPressed = RGB.DARK_BLUE
        On = RGB.GREEN
        Off = RGB.RED
        LockOn = RGB.YELLOW
        LockOff = RGB.DARK_BLUE

        class Bank(object):
            Navigation = RGB.DARK_BLUE
            NavigationPressed = RGB.LIGHT_BLUE

    class Mixermodes(object):
        class Volumemode(object):
            On = RGB.LIGHT_BLUE
            Off = RGB.OFF
        class Panmode(object):
            On = RGB.PURPLE
            Off = RGB.OFF

    class Controlmodes(object):
        class Mixingmode(object):
            On = RGB.YELLOW
            Off = RGB.OFF

        class Devicemode(object):
            On = RGB.ORANGE
            Off = RGB.OFF


class TwisterElements(ElementsBase):

    def reset_leds(self):
        for btn in self.buttons_raw:
            btn.reset()

        for enc in self.encoders_raw:
            enc.reset()

    def __init__(self, *a, **k):
        super().__init__(*a, **k)

        ids = []
        for row in range(4):
            ids.append([])
            for col in range(4):
                ids[-1].append(col+4*row)

        self.add_encoder_matrix(
            identifiers=ids,
            base_name="encoders",
            channels=0,
            needs_takeover=False,
            is_feedback_enabled=True,
        )
        self.add_submatrix(self.encoders, "top_encoders", columns=(0, 4), rows=(0, 2))
        self.add_submatrix(self.encoders, "bottom_encoders", columns=(0, 4), rows=(2, 4))


        self.add_button_matrix(
            identifiers=ids,
            base_name="buttons",
            channels=1,
        )
        self.add_submatrix(self.buttons, "top_buttons", columns=(0, 4), rows=(0, 2))
        self.add_submatrix(self.buttons, "bottom_buttons", columns=(0, 4), rows=(2, 4))


def create_mappings(control_surface):
    mappings = {}
    mappings["Mixer"] = {}
    mappings["Device"] = {}
    mappings["Device_Navigation"] = {}
    mappings["Session"] = {}
    mappings["Session_Overview"] = {}
    mappings["Session_Navigation"] = {}

    session_nav = lambda: {
        "component": "Session_Navigation",
        "page_left_button": "buttons_raw[13]",
        "page_right_button": "buttons_raw[14]",
    }
    cycle_mixer_mode = lambda: {
        "component": "MixerModes",
        "cycle_mode_button": "buttons_raw[12]",
    }

    select_tracks = lambda: {
        "component": "Mixer",
        "track_select_buttons": "top_buttons",
        "target_track_send_controls": "bottom_encoders",
        "target_track_mute_button": "buttons_raw[8]",
        "target_track_solo_button": "buttons_raw[9]",
        "target_track_arm_button": "buttons_raw[10]",
    }

    mappings["MixerModes"] = {
        "modes_component_type": ModesComponent,
        "enable": False,
        "VolumeMode": {
            "modes": [
                {
                    "component": "Mixer",
                    "volume_controls": "top_encoders",
                },
                select_tracks(),
                session_nav(),
                cycle_mixer_mode(),
            ]
        },
        "PanMode": {
            "modes": [
                {
                    "component": "Mixer",
                    "pan_controls": "top_encoders",
                },
                select_tracks(),
                session_nav(),
                cycle_mixer_mode(),
            ]
        },
    }

    cycle_control_mode = lambda: {
        "component": "ControlModes",
        "cycle_mode_button": "buttons_raw[15]",
    }
    mappings["ControlModes"] = {
        "modes_component_type": ModesComponent,
        "MixingMode": {
            "modes": [
                lambda: control_surface.elements.reset_leds(),
                {
                    "component": "MixerModes",
                },
                cycle_control_mode(),
            ]
        },
        "DeviceMode": {
            "modes": [
                lambda: control_surface.elements.reset_leds(),
                cycle_control_mode(),
                {
                    "component": "Device_Navigation",
                    "prev_button": "buttons_raw[13]",
                    "next_button": "buttons_raw[14]",
                },
                {
                    "component": "Device",
                    "parameter_controls": "encoders",
                    "prev_bank_button": "buttons_raw[9]",
                    "next_bank_button": "buttons_raw[10]",
                    "device_on_off_button": "buttons_raw[0]",
                    "device_lock_button": "buttons_raw[1]",
                },
            ]
        },
    }
    return mappings

SYSEX_START = 240

class Specification(ControlSurfaceSpecification):
    elements_type = TwisterElements
    num_tracks = 8
    num_scenes = 1
    link_session_ring_to_track_selection = False
    link_session_ring_to_scene_selection = False
    include_returns = True
    control_surface_skin = Skin(Colors)
    parameter_bank_size = 16
    create_mappings_function = create_mappings
    custom_identity_response = bytes(SYSEX_START)



class MGTwister2(ControlSurface):

    def __init__(self, c_instance):
        super().__init__(c_instance=c_instance, specification=Specification)
        # log(f"components: {self.components}")
        self.set_can_update_controlled_track(True)
        is_identifiable = self.specification.identity_response_id_bytes is not None or self.specification.custom_identity_response is not None
        # log(f"id?: {is_identifiable}")
        # log(f"id_resp_bytes {self.specification.identity_response_id_bytes}")
        # log(f"custom_id_response {self.specification.custom_identity_response }")
        # log(f"identified?: {self._identification.is_identified}")
        # log(f"can enable sess ring?: {self._can_enable_session_ring}")
        self._session_ring.set_enabled(True)

    def setup(self):
        super().setup()
        device = self.component_map["Device"]
        device._banking_info._num_simultaneous_banks = 1

        log(f"banking info {device._banking_info}")
        log(f"num sim {device._banking_info._num_simultaneous_banks}")
        log(f"bank registry {self.device_bank_registry}")

    #     self.component_map['Background'] = self._background
    #     self.component_map['Target_Track'] = self._target_track
    #     log(f"target track {self._target_track}")

    #     log(f"Compoment names {self.component_map.keys()}")

    #     mappings = self.specification.create_mappings_function(self)
    #     log(f"mappings {mappings.keys()}")

    #     component_names = self.component_map.keys()
    #     for name in list(mappings.keys()):
    #         if name in component_names:
    #             self._create_component(name, mappings.pop(name))

    #     for name, section in mappings.items():
    #         if name not in component_names:
    #             self._create_modes_component(name, section)

    #     for name, section in mappings.items():
    #         self._setup_modes_component(name, section)

    #     session_navigation = self.component_map["Session_Navigation"]
    #     log(f"Session Nav enabled? {session_navigation._is_enabled}")

    # def _create_component(self, name, component_mappings):
    #     should_enable = component_mappings.pop('enable', True)
    #     log(f"Creating component {name}, {component_mappings} enable? {should_enable}")
    #     component = self.component_map[name]
    #     component.layer = Layer(**component_mappings)
    #     component.set_enabled(should_enable)

    # def _create_modes_component(self, name, modes_config):
    #     log(f"Creating modes component {name}, {modes_config}")
    #     modes_component_type = modes_config.pop('modes_component_type', ModesComponent)
    #     component = modes_component_type(name=name,
    #       is_enabled=False,
    #       is_private=(modes_config.pop('is_private', False)),
    #       default_behaviour=(modes_config.pop('default_behaviour', None)),
    #       support_momentary_mode_cycling=(modes_config.pop('support_momentary_mode_cycling', True)))
    #     self.component_map[name] = component

    # def _setup_modes_component(self, name, modes_config):
    #     log(f"Setting up modes component {name}, {modes_config}")
    #     should_enable = modes_config.pop('enable', True)
    #     component = self.component_map[name]
    #     mode_control_layer = {}
    #     for mode_or_control_name, mode_or_element in modes_config.items():
    #         # log(f"mode/control {mode_or_control_name} {mode_or_element}")
    #         if isinstance(mode_or_element, str):
    #             mode_control_layer[mode_or_control_name] = mode_or_element
    #             continue
    #         else:
    #             self._add_mode(mode_or_control_name, mode_or_element, component)

    #     component.layer = Layer(**mode_control_layer)
    #     if component.selected_mode is None:
    #         log(f"set selected mod {component.modes[0]}")
    #         component.selected_mode = component.modes[0]
    #     component.set_enabled(should_enable)

    # def _add_mode(self, mode_name, mode_spec, modes_component):
    #     log(f"Adding mode {mode_name} {mode_spec} {modes_component}")
    #     is_dict = isinstance(mode_spec, dict)
    #     behaviour = mode_spec.pop('behaviour', None) if is_dict else None
    #     selector = mode_spec.pop('selector', None) if is_dict else None
    #     mode = mode_spec
    #     if is_dict:
    #         if 'modes' in mode_spec:
    #             mode = [self._create_mode_part(m) for m in mode_spec.pop('modes')]
    #         else:
    #             mode = self._create_mode_part(mode_spec)
    #     modes_component.add_mode(mode_name, mode, behaviour=behaviour, selector=selector)

    # def _create_mode_part(self, mode_mappings):
    #     log(f"create mode part {mode_mappings}")
    #     if isinstance(mode_mappings, dict):
    #         component = self.component_map[mode_mappings.pop('component')]
    #         if mode_mappings:
    #             return EnablingAddLayerMode(component=component,
    #               layer=Layer(**mode_mappings))
    #         return component
    #     return mode_mappings

    # def _create_identification(self, specification):
    #     log("Creating ID")
    #     identification = IdentificationComponent(identity_request=(specification.identity_request),
    #       identity_request_delay=(specification.identity_request_delay),
    #       identity_response_id_bytes=(specification.identity_response_id_bytes),
    #       custom_identity_response=(specification.custom_identity_response))
    #     self._ControlSurface__on_is_identified_changed.subject = identification
    #     return identification
