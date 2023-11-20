import logging
from functools import partial

# from ableton.v3 import midi
from ableton.v3.base import listens, depends, listenable_property, nop, task
from ableton.v3.control_surface import (
    ControlSurface,
    ControlSurfaceSpecification,
    BankingInfo,
    ElementsBase,
    MapMode,
    Layer,
    Skin,
    MIDI_CC_TYPE,
)
from ableton.v3.control_surface.elements import SimpleColor, EncoderElement, ButtonElement, ButtonMatrixElement
from ableton.v3.control_surface.components import (
    MixerComponent,
    SessionRingComponent,
    SessionComponent,
    DeviceComponent,
    ViewControlComponent,
    SimpleDeviceNavigationComponent,
    DeviceBankNavigationComponent,
)
from ableton.v3.control_surface.mode import ModesComponent, AddLayerMode, CompoundMode, EnablingAddLayerMode

logger = logging.getLogger(__name__)

def log(msg):
    logger.info(f"MGTwister2: {msg}")

# def f(self, mode_name):
#     out = '{}.{}'.format(self.name.title().replace('_', ''), mode_name.title().replace('_', ''))
#     log(f"mode name {self}, {mode_name}: {out}")
#     return out
# ModesComponent._get_mode_color_base_name = f
# def create_responder(identity_response_id_bytes, custom_identity_response):
#     if identity_response_id_bytes is not None:
#         return StandardResponder(identity_response_id_bytes)
#     if custom_identity_response[0] == midi.SYSEX_START:
#         return CustomSysexResponder(custom_identity_response)
#     return PlainMidiResponder(custom_identity_response)

# class IdentificationComponent(Component, Renderable):
#     identity_response_control = InputControl()
#     is_identified = listenable_property.managed(False)
#     received_response_bytes = listenable_property.managed(None)

#     @depends(send_midi=None)
#     def __init__(self, name='Identification', identity_request=midi.SYSEX_IDENTITY_REQUEST_MESSAGE, identity_request_delay=0.0, identity_response_id_bytes=None, custom_identity_response=None, send_midi=None, *a, **k):
#         (super().__init__)(a, name=name, **k)
#         self._send_midi = send_midi
#         self._identity_request = identity_request
#         self._responder = create_responder(identity_response_id_bytes, custom_identity_response)
#         response_element = self._responder.create_response_element()
#         response_element.name = 'identity_control'
#         response_element.is_private = True
#         self.identity_response_control.set_control_element(response_element)
#         self._request_task = self._tasks.add(task.sequence(task.run(self._send_identity_request), task.wait(identity_request_delay), task.run(self._send_identity_request)))
#         self._request_task.kill()

#     @identity_response_control.value
#     def identity_response_control(self, response_bytes, _):
#         try:
#             if self._responder.is_valid_response(response_bytes):
#                 self._request_task.kill()
#                 self.identity_response_control.enabled = False
#                 self.received_response_bytes = response_bytes
#                 self.is_identified = True
#                 self.notify(self.notifications.identify)
#         except IdentityResponseError as e:
#             try:
#                 logger.error(e)
#             finally:
#                 e = None
#                 del e

#     def request_identity(self):
#         self._request_task.restart()
#         self.received_response_bytes = None
#         self.is_identified = False

#     def _send_identity_request(self):
#         self.identity_response_control.enabled = True
#         self._send_midi(self._identity_request)

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
    # mappings["Session_Ring"] = {
    #     "num_tracks": control_surface.specification.num_tracks,
    #     "num_scenes": control_surface.specification.num_scenes,
    #     "enable": True,
    # }
    mappings["Mixer"] = {}
    mappings["Device"] = {}
    mappings["Device_Navigation"] = {}
    mappings["Session"] = {}
    mappings["Session_Overview"] = {}
    mappings["Session_Navigation"] = {}
    # mappings["Session_Ring"] = {}

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
        "cycle_mode_button": "buttons_raw[12]",
    }
    mappings["ControlModes"] = {
        "modes_component_type": ModesComponent,
        "DeviceMode": {
            "modes": [
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
        "MixingMode": {
            "modes": [
                cycle_control_mode(),
                # {
                #     "component": "Device_Navigation",
                #     "prev_button": "buttons_raw[13]",
                # }
            ]
        },
    }
    return mappings

def create_component_map():
    return {
        # "Session":
        # "Mixer": partial(MixerComponent, session_ring=SessionRingComponent(),
        # "Session_Ring": SessionRingComponent,
        # "Device_Bank_Navigation": DeviceBankNavigationComponent,
    #     # "Session": SessionComponent,
    }

SYSEX_START = 240

class Specification(ControlSurfaceSpecification):
    elements_type = TwisterElements
    num_tracks = 8
    num_scenes = 1
    link_session_ring_to_track_selection = True
    link_session_ring_to_scene_selection = True
    control_surface_skin = Skin(Colors)
    parameter_bank_size = 16
    component_map = create_component_map()
    create_mappings_function = create_mappings
    custom_identity_response = bytes(SYSEX_START)



class MGTwister2(ControlSurface):

    def __init__(self, c_instance):
        super().__init__(c_instance=c_instance, specification=Specification)
        log(f"components: {self.components}")
        self.set_can_update_controlled_track(True)
        is_identifiable = self.specification.identity_response_id_bytes is not None or self.specification.custom_identity_response is not None
        log(f"id?: {is_identifiable}")
        log(f"id_resp_bytes {self.specification.identity_response_id_bytes}")
        log(f"custom_id_response {self.specification.custom_identity_response }")
        log(f"identified?: {self._identification.is_identified}")
        log(f"can enable sess ring?: {self._can_enable_session_ring}")
        self._session_ring.set_enabled(True)

    @listens('is_identified')
    def __on_is_identified_changed(self, is_identified):
        log(f"ID changed {is_identified}")
        if is_identified:
            self.on_identified(self._identification.received_response_bytes)
        if self._can_enable_session_ring:
            self._session_ring.set_enabled(is_identified)
        self._update_auto_arm()

    # def setup(self):
    #     super().setup()
    #     log("Setup")

    #     self._create_mixer()

    #     # # create components
    #     # self._create_device_parameters()
    #     # self._create_view_control()
    #     # self._create_device_navigation()

    #     # # create modes
    #     # self._create_modes()



    def setup(self):
        log("Base Setup")
        # super().setup()

        self.component_map['Background'] = self._background
        self.component_map['Target_Track'] = self._target_track

        log(f"Compoment names {self.component_map.keys()}")

        mappings = self.specification.create_mappings_function(self)
        log(f"mappings {mappings.keys()}")

        component_names = self.component_map.keys()
        for name in list(mappings.keys()):
            if name in component_names:
                self._create_component(name, mappings.pop(name))

        for name, section in mappings.items():
            if name not in component_names:
                self._create_modes_component(name, section)

        for name, section in mappings.items():
            self._setup_modes_component(name, section)

        session_navigation = self.component_map["Session_Navigation"]
        log(f"Session Nav enabled? {session_navigation._is_enabled}")

        # session_ring = self.component_map["Session_Ring"]
        # log(f"Session Ring enabled? {session_ring._is_enabled}")
        # session_ring.num_tracks = self.specification.num_tracks
        # session_ring.num_scenes = self.specification.num_scenes
        # log(f"Session Ring num tracks {session_ring.num_tracks}, scenes {session_ring.num_scenes}")

    def _create_component(self, name, component_mappings):
        should_enable = component_mappings.pop('enable', True)
        log(f"Creating component {name}, {component_mappings} enable? {should_enable}")
        component = self.component_map[name]
        component.layer = Layer(**component_mappings)
        component.set_enabled(should_enable)

    def _create_modes_component(self, name, modes_config):
        log(f"Creating modes component {name}, {modes_config}")
        modes_component_type = modes_config.pop('modes_component_type', ModesComponent)
        component = modes_component_type(name=name,
          is_enabled=False,
          is_private=(modes_config.pop('is_private', False)),
          default_behaviour=(modes_config.pop('default_behaviour', None)),
          support_momentary_mode_cycling=(modes_config.pop('support_momentary_mode_cycling', True)))
        self.component_map[name] = component

    def _setup_modes_component(self, name, modes_config):
        log(f"Setting up modes component {name}, {modes_config}")
        should_enable = modes_config.pop('enable', True)
        component = self.component_map[name]
        mode_control_layer = {}
        for mode_or_control_name, mode_or_element in modes_config.items():
            # log(f"mode/control {mode_or_control_name} {mode_or_element}")
            if isinstance(mode_or_element, str):
                mode_control_layer[mode_or_control_name] = mode_or_element
                continue
            else:
                self._add_mode(mode_or_control_name, mode_or_element, component)

        component.layer = Layer(**mode_control_layer)
        if component.selected_mode is None:
            log(f"set selected mod {component.modes[0]}")
            component.selected_mode = component.modes[0]
        component.set_enabled(should_enable)

    def _add_mode(self, mode_name, mode_spec, modes_component):
        log(f"Adding mode {mode_name} {mode_spec} {modes_component}")
        is_dict = isinstance(mode_spec, dict)
        behaviour = mode_spec.pop('behaviour', None) if is_dict else None
        selector = mode_spec.pop('selector', None) if is_dict else None
        mode = mode_spec
        if is_dict:
            if 'modes' in mode_spec:
                mode = [self._create_mode_part(m) for m in mode_spec.pop('modes')]
            else:
                mode = self._create_mode_part(mode_spec)
        modes_component.add_mode(mode_name, mode, behaviour=behaviour, selector=selector)

    def _create_mode_part(self, mode_mappings):
        log(f"create mode part {mode_mappings}")
        if isinstance(mode_mappings, dict):
            component = self.component_map[mode_mappings.pop('component')]
            if mode_mappings:
                return EnablingAddLayerMode(component=component,
                  layer=Layer(**mode_mappings))
            return component
        return mode_mappings

    # def _create_identification(self, specification):
    #     log("Creating ID")
    #     identification = IdentificationComponent(identity_request=(specification.identity_request),
    #       identity_request_delay=(specification.identity_request_delay),
    #       identity_response_id_bytes=(specification.identity_response_id_bytes),
    #       custom_identity_response=(specification.custom_identity_response))
    #     self._ControlSurface__on_is_identified_changed.subject = identification
    #     return identification
