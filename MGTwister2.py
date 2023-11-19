import logging
from functools import partial

from ableton.v3.base import listens
from ableton.v3.control_surface import (
    ControlSurface,
    ControlSurfaceSpecification,
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
)
from ableton.v3.control_surface.mode import ModesComponent, AddLayerMode, CompoundMode, EnablingAddLayerMode

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
        TrackSelected = RGB.RED
        TrackNotSelected = RGB.ORANGE

    class Device(object):
        Navigation = RGB.ORANGE
        NavigationPressed = RGB.RED

    class Mode(object):
        class Volume(object):
            On = RGB.LIGHT_BLUE
            # Off = RGB.OFF

        class Pan(object):
            On = RGB.PURPLE
            # Off = RGB.OFF

        class MixerMode(object):
            On = RGB.ORANGE
            Off = RGB.RED


class TwisterElements(ElementsBase):

    # def reset_leds(self):
    #     for btn_row in self.buttons:
    #         for btn in btn_row:
    #             btn.reset()

    #     for enc_row in self.encoders:
    #         for enc in enc_row:
    #             enc.reset()

    def __init__(self, *a, **k):
        super().__init__(*a, **k)

        ids = []
        for row in range(4):
            ids.append([])
            for col in range(4):
                ids[-1].append(col+4*row)
                self.add_encoder(identifier=ids[-1][-1], name=f"button_{col}_{row}", channel=0)
                self.add_button(identifier=ids[-1][-1], name=f"button_{col}_{row}", channel=1)

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

        # log(f"Elements methods: {dir(self)}")
        # log(f"RAW encoders: {self.encoders_raw}")

def create_mappings(control_surface):
    mappings = {}
    # mappings["Session_Ring"] = {
    #     "num_tracks": control_surface.specification.num_tracks,
    #     "num_scenes": control_surface.specification.num_scenes,
    #     "enable": True,
    # }
    mappings["Mixer"] = {
    }
    mappings["MixerMode"] = {
        "modes_component_type": ModesComponent,
        "enable": True,
        "VolumeMode": {
            "component": "Mixer",
            "volume_controls": "top_encoders"
        }
    }
    return mappings

def create_compoment_map():
    return {
        # "Mixer": partial(MixerComponent, session_ring=SessionRingComponent(),
    #     "Session_Ring": SessionRingComponent,
    #     # "Session": SessionComponent,
    }

class Specification(ControlSurfaceSpecification):
    elements_type = TwisterElements
    num_tracks = 8
    num_scenes = 1
    link_session_ring_to_track_selection = False
    control_surface_skin = Skin(Colors)
    parameter_bank_size = 16
    component_map = create_compoment_map()
    create_mappings_function = create_mappings


class MGTwister2(ControlSurface):

    def __init__(self, c_instance):
        super().__init__(c_instance=c_instance, specification=Specification)
        log(f"components: {self.components}")
        self.set_can_update_controlled_track(True)

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

        log(f"Mixer: {self.component_map['Mixer']} {dir(self.component_map['Mixer'])}")

        mixer = self.component_map["Mixer"]
        log(f"Mixer enabled? {mixer._is_enabled}")
        mixer.set_enabled(True)
        session_navigation = self.component_map["Session_Navigation"]

        # self._mixer_modes = ModesComponent(
        #     name="mixer_modes",
        #     is_enabled=False,
        #     layer=Layer(cycle_mode_button="button_3_0"),
        # )

        # selected_track_controls = (
        #     AddLayerMode(
        #         mixer.target_strip,
        #         Layer(
        #             mute_button="button_2_0",
        #             solo_button="button_2_1",
        #             arm_button="button_2_2",
        #             send_controls="bottom_encoders",
        #         ),
        #     ),
        # )

        # track_selection = (
        #     AddLayerMode(
        #         mixer,
        #         Layer(
        #             track_select_buttons="top_buttons",
        #         ),
        #     ),
        # )

        # box_navigation = (
        #     AddLayerMode(
        #         session_navigation,
        #         layer=Layer(
        #             page_left_button="button_3_1",
        #             page_right_button="button_3_2",
        #         ),
        #     ),
        # )

        # self._mixer_modes.add_mode(
        #     "volume",
        #     CompoundMode(
        #         AddLayerMode(
        #             mixer,
        #             Layer(
        #                 volume_controls="top_encoders",
        #             ),
        #         ),
        #         track_selection,
        #         selected_track_controls,
        #         box_navigation,
        #     ),
        #     # cycle_mode_button_color="Mode.Volume.On",
        # )
        # self._mixer_modes.add_mode(
        #     "pan",
        #     CompoundMode(
        #         AddLayerMode(
        #             mixer,
        #             Layer(
        #                 pan_controls="top_encoders",
        #             ),
        #         ),
        #         track_selection,
        #         selected_track_controls,
        #         box_navigation,
        #     ),
        #     # cycle_mode_button_color="Mode.Pan.On",
        # )
        # self._mixer_modes.selected_mode = "volume"
        # self._mixer_modes.set_enabled(False)

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
            log(f"mode/control {mode_or_control_name} {mode_or_element}")
            if isinstance(mode_or_element, str):
                log("string mode")
                mode_control_layer[mode_or_control_name] = mode_or_element
                continue
            else:
                log("adding mode")
                self._add_mode(mode_or_control_name, mode_or_element, component)

        component.layer = Layer(**mode_control_layer)
        log("set selected mode")
        if component.selected_mode is None:
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
