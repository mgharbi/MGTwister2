import logging
from contextlib import contextmanager
from future.moves.itertools import zip_longest

import Live

import math

from ableton.v2.base import const, inject, nop, depends, listens, liveobj_valid
from ableton.v2.control_surface import ControlSurface, Skin, Layer, BankingInfo
from ableton.v2.control_surface.device_parameter_bank import MaxDeviceParameterBank, DescribedDeviceParameterBank, DeviceParameterBank
from ableton.v2.control_surface.elements import Color
# from ableton.v3.control_surface.components.device_bank_navigation import DeviceBankNavigationComponent as DeviceBankNavigationComponentV3
from ableton.v2.control_surface import MIDI_CC_TYPE, MIDI_NOTE_TYPE, ParameterProvider
from ableton.v2.control_surface.control import ButtonControl
from ableton.v2.control_surface.components import (
    SessionComponent,
    DeviceComponent,
    DeviceNavigationComponent,
    DeviceParameterComponent,
    SessionRecordingComponent,
    SessionRingComponent,
    SessionNavigationComponent,
    SimpleTrackAssigner,
    ChannelStripComponent,
    MixerComponent,
)
from ableton.v2.control_surface.elements import (
    ButtonElement,
    EncoderElement,
    ButtonMatrixElement,
    SliderElement,
    SysexElement,
)
from ableton.v2.control_surface.mode import (
    ModesComponent,
    EnablingMode,
    EnablingModesComponent,
    LayerMode,
    AddLayerMode,
    CompoundMode,
)
from novation.simple_device import SimpleDeviceParameterComponent
from novation.simple_device_navigation import SimpleDeviceNavigationComponent

logger = logging.getLogger(__name__)


class RGB(object):
    OFF = Color(0)

    DARK_BLUE = Color(1)
    LIGHT_BLUE = Color(25)
    TURQUOISE = Color(37)
    GREEN = Color(43)
    YELLOW = Color(61)
    ORANGE = Color(69)
    RED = Color(78)
    PINK = Color(97)
    PURPLE = Color(113)
    AQUA = Color(127)


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

def custom_create_device_bank(device, banking_info):
    bank = None
    if liveobj_valid(device):
        if banking_info.has_bank_count(device):
            bank_class = MaxDeviceParameterBank
        else:
            if banking_info.device_bank_definition(device) is not None:
                bank_class = DescribedDeviceParameterBank
            else:
                bank_class = DeviceParameterBank
        bank = bank_class(device=device, size=16, banking_info=banking_info)
    return bank
            
class CustomEncoder(EncoderElement):
    def release_parameter(self):
        super().release_parameter()
        self.reset()

class CustomButton(ButtonElement):
    def release_parameter(self):
        super().release_parameter()
        self.reset()
        

class CustomDeviceComponent(DeviceComponent):

    next_bank_button = ButtonControl(color='Device.Navigation',
      pressed_color='Device.NavigationPressed')
    prev_bank_button = ButtonControl(color='Device.Navigation',
      pressed_color='Device.NavigationPressed')

    def _create_parameter_info(self, parameter, name):
        logger.info(f"custom device {parameter} {name}")
        return parameter

    def _current_bank_details(self):
        logger.info(f"current bank detail: {self._bank}")
        if self._bank is not None:
            logger.info(f"bank name {self._bank.name} {self._bank.parameters}")
        if self._bank is not None:
            return (self._bank.name, self._bank.parameters)
        return (
         '', [None] * 16)

    @next_bank_button.pressed
    def next_bank_button(self, value):
        logger.info(f"pressed_next_bank")

    @prev_bank_button.pressed
    def prev_bank_button(self, value):
        logger.info(f"pressed_prev_bank")

    def _setup_bank(self, device, bank_factory=custom_create_device_bank):
        if self._bank is not None:
            self.disconnect_disconnectable(self._bank)
            self._bank = None
        if liveobj_valid(device):
            self._bank = self.register_disconnectable(bank_factory(device, self._banking_info))

class CustomDeviceParameterComponent(DeviceParameterComponent):
    controls = None

    def set_parameter_controls(self, encoder_matrix):
        self.controls = encoder_matrix
        self._connect_parameters()

    def _connect_parameters(self):
        if self.controls is None:
            logger.info("no controls, not connecting")
            return
        logger.info(f"connecting {self.controls} {len(self.controls)}")
        print("provider params:", self._parameter_provider.parameters, len(self._parameter_provider.parameters))
        parameters = self._parameter_provider.parameters[:len(self.controls)]
        logger.info(f"provider {self._parameter_provider} params: {len(parameters)}")

        for control, parameter in zip_longest(self.controls, parameters):
            if liveobj_valid(control):
                logger.info(f"valid control {control}")
                if liveobj_valid(parameter):
                    logger.info(f"valid param {parameter}, connecting to {control}")
                    control.connect_to(parameter)
                else:
                    logger.info(f"invalid param {parameter}, releasing {control}")
                    control.release_parameter()
            else:
                logger.info(f"valid control {control}")


@depends(skin=None)
def create_button(page, x, y, is_momentary=True, **k):
    """Get the button at (x, y) on page <page>.

    The MF Twister has 4 pages of encoders with 4x4 controls for each page.

    ---------------
    |  0  1  2  3 |
    |  4  5  6  7 |
    |  8  9 10 11 |
    | 12 13 14 15 |
    ---------------
    """
    assert page >= 0 and page < 4, "page should be in [0, 4["
    assert x >= 0 and x < 4, "x coordinate should be in [0, 4["
    assert y >= 0 and y < 4, "y coordinate should be in [0, 4["

    cc = x + 4 * (y + 4 * page)

    button = CustomButton(
        is_momentary, MIDI_CC_TYPE, 1, cc, name=f"button_{x}_{y}", **k
    )

    logger.info(f"button {x} {y} set")

    return button


def create_encoder(page, x, y, **k):
    """Get the encoder at (x, y) on page <page>.

    The MF Twister has 4 pages of encoders with 4x4 controls for each page.

    ---------------
    |  0  1  2  3 |
    |  4  5  6  7 |
    |  8  9 10 11 |
    | 12 13 14 15 |
    ---------------
    """
    assert page >= 0 and page < 4, "page should be in [0, 4["
    assert x >= 0 and x < 4, "x coordinate should be in [0, 4["
    assert y >= 0 and y < 4, "y coordinate should be in [0, 4["

    cc = x + 4 * (y + 4 * page)

    ENCODER_CHANNEL = 0
    MAP_MODE = Live.MidiMap.MapMode.absolute
    encoder = CustomEncoder(
        MIDI_CC_TYPE, ENCODER_CHANNEL, cc, MAP_MODE, name=f"encoder_{x}_{y}", **k
    )

    logger.info(f"Setting encoder {x},{y} on page {page} with cc {cc}")

    return encoder


class TwisterElements(object):
    def reset_leds(self):
        for btn_row in self.buttons:
            for btn in btn_row:
                btn.reset()

        for enc_row in self.encoders:
            for enc in enc_row:
                enc.reset()

    def __init__(self, *a, **k):
        (super().__init__)(*a, **k)

        self.buttons = []
        self.encoders = []
        for y in range(4):
            buttons_row = []
            encoders_row = []
            for x in range(4):
                btn = create_button(0, x, y)
                enc = create_encoder(0, x, y)
                setattr(self, f"button_{y}_{x}", btn)
                setattr(self, f"encoder_{y}_{x}", btn)
                buttons_row.append(btn)
                encoders_row.append(enc)
            self.buttons.append(buttons_row)
            self.encoders.append(encoders_row)

        self.buttons_matrix = ButtonMatrixElement(
            rows=self.buttons,
            name="buttons_matrix",
        )

        self.encoders_matrix = ButtonMatrixElement(
            rows=self.encoders,
            name="encoders_matrix",
        )

        for y in range(1, 4):
            mtx = ButtonMatrixElement(
                rows=self.encoders[:y],
                name=f"encoders_top{y}",
            )
            setattr(self, f"encoders_top{y}", mtx)

            mtx = ButtonMatrixElement(
                rows=self.buttons[:y],
                name=f"buttons_top{y}",
            )
            setattr(self, f"buttons_top{y}", mtx)

            mtx = ButtonMatrixElement(
                rows=self.encoders[4 - y :],
                name=f"encoders_bottom{y}",
            )
            setattr(self, f"encoders_bottom{y}", mtx)

            mtx = ButtonMatrixElement(
                rows=self.buttons[4 - y :],
                name=f"buttons_bottom{y}",
            )
            setattr(self, f"buttons_bottom{y}", mtx)


class MGTwister2(ControlSurface):
    skin = Skin(Colors)

    def __init__(self, *a, num_tracks=8, **k):
        super().__init__(*a, **k)

        self._element_injector = inject(element_container=(const(None))).everywhere()

        self.num_tracks = num_tracks

        with self.component_guard():
            with inject(skin=(const(self.skin))).everywhere():
                self._elements = TwisterElements()
        self._element_injector = inject(
            element_container=(const(self._elements))
        ).everywhere()

        with self.component_guard():
            self._create_components()

        self.show_message("MGTwister2 active")

    @contextmanager
    def _component_guard(self):
        with super()._component_guard():
            with self._element_injector:
                yield

    def _create_components(self):
        self._create_session()

        self._create_mixer()
        self._create_device()
        self._create_modes()

        # self._global_modes.add_mode(
        #     "mixer_mode", AddLayerMode(self._mixer_modes, Layer(enabled=True))
        # )

    def _create_device(self):
        self._device = CustomDeviceComponent(
            banking_info=BankingInfo({}), device_bank_registry=self._device_bank_registry)
        # self._bank_nav = DeviceBankNavigationComponentV3(device_bank_registry=self._device_bank_registry)
        self._device_parameters = CustomDeviceParameterComponent(
            parameter_provider=self._device,
            name="Device_Parameters_Component",
        )

        # self._device_navigation = DeviceNavigationComponent(self._device)
        self._device_navigation = SimpleDeviceNavigationComponent()

        # logger.info(f"old provider: {self._device_parameters.parameter_provider}")
        # self._device_parameters.parameter_provider = self._device
        # self._device_parameters = SimpleDeviceParameterComponent(
        #     name="Device_Parameters_Component"
        # )
        # logger.info(f"Created device {type(self.device_provider)}")

        # TODO(bank next buttons)

    def _create_modes(self):
        self._global_modes = ModesComponent(
            name="global_modes",
            is_enabled=False,
            layer=Layer(cycle_mode_button="button_3_3"),
        )
        self._global_modes.add_mode(
            "mixer_controls",
            CompoundMode(
                lambda: self._elements.reset_leds(),
                EnablingMode(self._mixer_modes),
            ),
            cycle_mode_button_color="Mode.MixerMode.On",
        )
        self._global_modes.add_mode(
            "device_controls",
            CompoundMode(
                lambda: self._elements.reset_leds(),
                AddLayerMode(
                    self._device_parameters,
                    Layer(
                        parameter_controls="encoders_matrix",
                    ),
                ),
                # AddLayerMode(
                #     self._device,
                #     Layer(
                #         prev_bank_button="button_2_1",
                #         next_bank_button="button_2_2",
                #     ),
                # ),
                AddLayerMode(
                    self._bank_nav,
                    Layer(
                        prev_bank_button="button_2_1",
                        next_bank_button="button_2_2",
                    ),
                ),
                AddLayerMode(
                    self._device_navigation,
                    Layer(
                        prev_button="button_3_1",
                        next_button="button_3_2",
                    ),
                ),
            ),
            cycle_mode_button_color="Mode.MixerMode.Off",
        )
        self._global_modes.selected_mode = "mixer_controls"
        self._global_modes.set_enabled(True)

    def _create_session(self):
        self._session_ring = SessionRingComponent(
            name="Session_Ring",
            is_enabled=True,
            num_tracks=self.num_tracks,
            num_scenes=1,
        )
        self._session = SessionComponent(
            name="Session",
            is_enabled=True,
            session_ring=(self._session_ring),
        )
        self._session_navigation = SessionNavigationComponent(
            name="Session_Navigation",
            is_enabled=True,
            session_ring=(self._session_ring),
        )
        self._session_navigation.set_enabled(True)

    def _create_mixer(self):
        # TODO(mgharbi): clear LED when track is deleted
        self._mixer = MixerComponent(
            name="Mixer",
            auto_name=True,
            tracks_provider=(self._session_ring),
            invert_mute_feedback=False,
            channel_strip_component_type=ChannelStripComponent,
        )

        self._mixer_modes = ModesComponent(
            name="mixer_modes",
            is_enabled=False,
            layer=Layer(cycle_mode_button="button_3_0"),
        )

        selected_track_controls = (
            AddLayerMode(
                self._mixer.selected_strip(),
                Layer(
                    mute_button="button_2_0",
                    solo_button="button_2_1",
                    arm_button="button_2_2",
                    send_controls="encoders_bottom2",
                ),
            ),
        )
        track_selection = (
            AddLayerMode(
                self._mixer,
                Layer(
                    track_select_buttons="buttons_top2",
                ),
            ),
        )

        box_navigation = (
            AddLayerMode(
                self._session_navigation,
                layer=Layer(
                    page_left_button="button_3_1",
                    page_right_button="button_3_2",
                ),
            ),
        )

        self._mixer_modes.add_mode(
            "volume",
            CompoundMode(
                AddLayerMode(
                    self._mixer,
                    Layer(
                        volume_controls="encoders_top2",
                    ),
                ),
                track_selection,
                selected_track_controls,
                box_navigation,
            ),
            cycle_mode_button_color="Mode.Volume.On",
        )
        self._mixer_modes.add_mode(
            "pan",
            CompoundMode(
                AddLayerMode(
                    self._mixer,
                    Layer(
                        pan_controls="encoders_top2",
                    ),
                ),
                track_selection,
                selected_track_controls,
                box_navigation,
            ),
            cycle_mode_button_color="Mode.Pan.On",
        )
        self._mixer_modes.selected_mode = "volume"
        self._mixer_modes.set_enabled(False)

    def disconnect(self):
        super().disconnect()

