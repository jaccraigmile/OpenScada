PROGRAM main
VAR
    StartButton AT %IX100.0 : BOOL;
    SafetyDoor AT %IX100.1 : BOOL;
    Box_Not_Waiting AT %IX100.2 : BOOL;
    Picker_Holding_Box AT %IX100.3 : BOOL;
    Picker_Rotating AT %IX100.4 : BOOL;
    Picker_Moving_Z AT %IX100.5 : BOOL;

    Conveyor_Move AT %QX100.0 : BOOL;
    Picker_Move_Down AT %QX100.1 : BOOL := FALSE;
    Picker_Grab AT %QX100.2 : BOOL := FALSE;
    Picker_Rotate_CCW AT %QX100.3 : BOOL := FALSE;
    Picker_Rotate_CW AT %QX100.4 : BOOL := FALSE;

    RUN : BOOL;
    Box_Not_Waiting_Prev : BOOL := FALSE;
    Picker_Holding_Box_Prev : BOOL := FALSE;
    Picker_Moving_Z_Prev : BOOL := FALSE;
    Picker_Rotating_Prev : BOOL := FALSE;
END_VAR

RUN := StartButton AND SafetyDoor;
Conveyor_Move := RUN AND Box_Not_Waiting;

IF RUN AND Box_Not_Waiting_Prev AND NOT Box_Not_Waiting
   AND NOT Picker_Holding_Box THEN
    Picker_Move_Down := TRUE;
    Picker_Grab := TRUE;
END_IF;

IF RUN AND NOT Picker_Holding_Box_Prev AND Picker_Holding_Box THEN
    Picker_Move_Down := FALSE;
END_IF;

IF RUN AND Picker_Moving_Z_Prev AND NOT Picker_Moving_Z
   AND Picker_Holding_Box THEN
    Picker_Rotate_CCW := TRUE;
    Picker_Rotate_CW := FALSE;
END_IF;

IF RUN AND Picker_Rotating_Prev AND NOT Picker_Rotating
   AND Picker_Holding_Box THEN
    Picker_Grab := FALSE;
    Picker_Rotate_CW := TRUE;
    Picker_Rotate_CCW := FALSE;
END_IF;

Box_Not_Waiting_Prev := Box_Not_Waiting;
Picker_Holding_Box_Prev := Picker_Holding_Box;
Picker_Moving_Z_Prev := Picker_Moving_Z;
Picker_Rotating_Prev := Picker_Rotating;
END_PROGRAM
