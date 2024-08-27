from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set, Dict, Any
from itertools import product
from mavros_msgs.msg import ParamValue

@dataclass
class Fuzz_Test:
    '''
    Class that stores all information on a fuzz test scenario.

    This class expects information on the fuzzing scenario. 
    If an argument is not provided, it is assumed that the parameter should be excluded from the test.
    For example, if conducting a geofence test, there is no need to pass in any states.

    Examples:
        Ex_1. Fuzz all MODE switches with all onboard STATES:
            modes= ['ALTCTL', 'POSCTL', 'OFFBOARD', 'STABILIZED', 'AUTO.LOITER', 'AUTO.RTL', 'AUTO.LAND'],
            states= ['Takeoff', 'BriarWaypoint', 'BriarHover', 'Land', 'Disarm']

        Ex_2. Fuzz geofence RTL with all mode switches:
            geofence: [1-5],
            modes - (list of full set of modes as above)

    Args:
        drone_id (str): Name of the drone, corresponding to a color.
        modes (List[str]): Mode switch requests. Defaults to an empty list.
        states (List[str]): Onboard states. Defaults to an empty list.
        geofence (List[str]): Geofence actions. Defaults to an empty list.
        throttle (List[int]): Throttle values. Defaults to an empty list. [1-5]
        wind (Optional[Tuple[int, str]]): Wind value and direction. Defaults to None.
        geofence_predict 
    '''

    drone_id: str 
    modes: List[str] = field(default_factory=list)
    states: List[str] = field(default_factory=list)
    geofence: List[str] = field(default_factory=list)
    throttle: List[int] = field(default_factory=list)
    wind: Optional[Tuple[int, str]] = None
    fuzz_type : str = ""
    command_template: Dict[str, Dict[str, Any]] = field(init=False)
    test_combinations: Set[Tuple] = field(default_factory=set)


    def __post_init__(self):
        # Generate and store test combinations
        self.test_combinations = self.generate_combinations()
        print('[Debug] Printing test combinations - '+str(self.test_combinations))
        self.setup_command_structure()
        # Initialize command_template based on provided configuration
        self.command_template = self.create_command_template()
        print('Command template - ', self.command_template)
    
    def generate_combinations(self) -> Set[Tuple]:
        '''
        Tuple structure is either:
        MODES,THROTTLES,STATES
        MODES,THROTTLES,GEOFENCE
        '''
        MODE_TO_THROTTLE = {
        "STABILIZED": [0, 225, 435, 445, 450],
        "POSCTL": [0, 260, 550, 600, 615],
        "ALTCTL": [0, 260, 550, 600, 615]
        }

        # the test must always have either a state listed or a geofence action 
        
        if self.geofence:
            self.fuzz_type += "geo"
            variable_list = self.geofence
            if self.modes:
                self.fuzz_type += "_mode"
            if self.throttle:
                self.fuzz_type += "_throttle"
            self.fuzz_type += "_geo"
        elif self.states:
            self.fuzz_type += "state"
            if self.modes:
                self.fuzz_type += "_mode"
            if self.throttle:
                self.fuzz_type += "_throttle"
            variable_list = self.states

        non_empty_lists = [lst for lst in [self.modes, self.throttle, variable_list] if lst]
        non_empty_lists_2 = [lst for lst in [self.modes, self.throttle] if lst]

        print('Non empty lists - ', non_empty_lists)
        
        # Generate combinations from non-empty lists
        all_combinations = set(product(*non_empty_lists))
        all_combinations_2 =  set(product(*non_empty_lists_2))

        print('All combinations - ', all_combinations)

        # Determine default mode for throttle mapping if no modes are provided
        default_mode = "POSCTL" if not self.modes else None

        if self.throttle:
            remapped_combinations = set()
            mode_index = non_empty_lists.index(self.modes) if self.modes in non_empty_lists else None
            throttle_index = non_empty_lists.index(self.throttle) if self.throttle in non_empty_lists else None
            for combination in all_combinations:
                mode = combination[mode_index] if mode_index is not None else "POSCTL"
                mode = mode if mode in MODE_TO_THROTTLE else "POSCTL"
                throttle_index_value = combination[throttle_index] if throttle_index is not None else None
                new_throttle = MODE_TO_THROTTLE[mode][throttle_index_value - 1]
                new_combination = list(combination)
                if throttle_index is not None:
                    new_combination[throttle_index] = new_throttle
                remapped_combinations.add(tuple(new_combination))
            print('Remapped Combinations - ', remapped_combinations)
            return remapped_combinations
        return all_combinations

    
    def remove_states_from_combinations(self) -> Set[Tuple]:
        """
        Remove state items from each tuple in the combinations set.

        Args:
            combinations (Set[Tuple]): A set of tuples where each tuple contains various items including states.
            states (Set): A set of items considered as states.

        Returns:
            Set[Tuple]: A new set with the same tuples but without the state items.
        """
        new_combinations = set()

        for combination in self.test_combinations:
            new_combination = tuple(item for item in combination if item not in self.states)
            new_combinations.add(new_combination)

        return new_combinations


    def setup_command_structure(self):
        index = 0
        if 'mode' in self.fuzz_type:
            self.mode_index = index
            index += 1
        if 'throttle' in self.fuzz_type:
            self.throttle_index = index
            index += 1
        if 'geo' in self.fuzz_type:
            self.geofence_index = index
            
    def create_command_template(self):
        command_dict = {}
        if "geo" in self.fuzz_type:
            command_dict['set_param'] = {'param_id': 'GF_ACTION', "value": None}
        if "_mode" in self.fuzz_type:
            command_dict['set_mode'] = {'custom_mode': None}
        if "_throttle" in self.fuzz_type:
             command_dict['set_throttle'] = {'throttle_value': None}
        return command_dict 

    def populate_command(self, test_tuple: Tuple) -> Dict[str, Dict[str, Any]]:
        command = self.command_template.copy()
        if hasattr(self, 'mode_index'):
            command['set_mode']['custom_mode'] = test_tuple[self.mode_index]
        if hasattr(self, 'throttle_index'):
            command['set_throttle']['throttle_value'] = test_tuple[self.throttle_index]
        if hasattr(self, 'geofence_index'):
            integer = test_tuple[self.geofence_index]
            value = ParamValue(integer,0.0)
            command['set_param']['value'] = value
        return command