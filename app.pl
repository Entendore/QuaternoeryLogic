%% quaternary.pl — Complete quaternary logic system
%% Load this file from Python via pyswip

:- use_module(library(clpfd)).

%% ═══════════════════════════════════════════════════════════════════
%% CORE GATES
%% ═══════════════════════════════════════════════════════════════════

q(X) :- integer(X), X >= 0, X =< 3.

notq(0, 3).  notq(1, 2).  notq(2, 1).  notq(3, 0).
cyc(0, 1).   cyc(1, 2).   cyc(2, 3).   cyc(3, 0).

qand(A, B, O) :- O is min(A, B).
qor(A, B, O)  :- O is max(A, B).
qnand(A, B, O):- O is 3 - min(A, B).
qnor(A, B, O) :- O is 3 - max(A, B).
qxor(A, B, O) :- O is (A + B) mod 4.
qimp(A, B, O) :- O is min(3, 3 - A + B).
qeq(A, B, O)  :- O is 3 - abs(A - B).

threshold(K, A, O) :- (A >= K -> O = 3 ; O = 0).
literal(K, A, O)   :- (A =:= K -> O = 3 ; O = 0).

%% ═══════════════════════════════════════════════════════════════════
%% DNA ANALYZER
%% ═══════════════════════════════════════════════════════════════════

nuc_q('A', 0).  nuc_q('C', 1).  nuc_q('G', 2).  nuc_q('T', 3).
q_nuc(0, 'A').  q_nuc(1, 'C').  q_nuc(2, 'G').  q_nuc(3, 'T').

dna_to_q([], []).
dna_to_q([N|Ns], [Q|Qs]) :-
    atom_chars(N, [C]),
    nuc_q(C, Q),
    dna_to_q(Ns, Qs).

q_to_dna([], []).
q_to_dna([Q|Qs], [N|Ns]) :-
    q_nuc(Q, C),
    atom_chars(N, [C]),
    q_to_dna(Qs, Ns).

dna_complement([], []).
dna_complement([Q|Qs], [C|Cs]) :-
    notq(Q, C),
    dna_complement(Qs, Cs).

dna_rev_comp(Seq, RC) :-
    dna_complement(Seq, Comp),
    reverse(Comp, RC).

gc_content([], 0, 0).
gc_content([Q|Qs], GC, Total) :-
    gc_content(Qs, GC0, Total0),
    Total is Total0 + 1,
    ( (Q =:= 1 ; Q =:= 2) -> GC is GC0 + 1 ; GC = GC0 ).

dna_hamming([], [], 0).
dna_hamming([Q1|Qs1], [Q2|Qs2], D) :-
    dna_hamming(Qs1, Qs2, D0),
    ( Q1 =:= Q2 -> D = D0 ; D is D0 + 1 ).

%% ═══════════════════════════════════════════════════════════════════
%% QPSK MODULATOR
%% ═══════════════════════════════════════════════════════════════════

qpsk_constellation(0,  45,  0.707,  0.707).
qpsk_constellation(1, 135, -0.707,  0.707).
qpsk_constellation(2, 225, -0.707, -0.707).
qpsk_constellation(3, 315,  0.707, -0.707).

qpsk_modulate(Symbol, I, Qc) :-
    qpsk_constellation(Symbol, _, I, Qc).

qpsk_demodulate(I, Qc, Symbol) :-
    findall(D-S,
        ( qpsk_constellation(S, _, Iref, Qref),
          D is (I - Iref)^2 + (Qc - Qref)^2
        ),
        Distances),
    sort(Distances, [_-Symbol|_]).

bits_to_qpsk([], []).
bits_to_qpsk([B1, B2|Rest], [iq(I, Q)|Syms]) :-
    Symbol is B1 * 2 + B2,
    qpsk_modulate(Symbol, I, Q),
    bits_to_qpsk(Rest, Syms).

%% ═══════════════════════════════════════════════════════════════════
%% FLASH MEMORY
%% ═══════════════════════════════════════════════════════════════════

voltage_level(0, 0.5).
voltage_level(1, 1.5).
voltage_level(2, 2.5).
voltage_level(3, 3.5).

read_cell(V, Value) :-
    ( V < 1.0 -> Value = 0
    ; V < 2.0 -> Value = 1
    ; V < 3.0 -> Value = 2
    ;            Value = 3
    ).

voltage_drift(V, Time, Vd) :-
    Leak is 0.01 * Time,
    Vd is max(0, V - Leak).

gray_encode(0, [0, 0]).
gray_encode(1, [0, 1]).
gray_encode(2, [1, 1]).
gray_encode(3, [1, 0]).

%% ═══════════════════════════════════════════════════════════════════
%% TRAFFIC LIGHT FSM
%% ═══════════════════════════════════════════════════════════════════

state_name(0, red).
state_name(1, yellow).
state_name(2, green).
state_name(3, off).

state_duration(0, 30).
state_duration(1, 5).
state_duration(2, 25).
state_duration(3, 0).

transition(red,    green).
transition(green,  yellow).
transition(yellow, red).

traffic_step(Current, Event, Next, Duration) :-
    state_name(Current, CName),
    ( Event = emergency   -> NName = red
    ; Event = maintenance -> NName = off
    ; Event = timer       -> transition(CName, NName)
    ; NName = CName
    ),
    state_name(Next, NName),
    state_duration(Next, Duration).

%% ═══════════════════════════════════════════════════════════════════
%% ELEVATOR
%% ═══════════════════════════════════════════════════════════════════

floor_name(0, basement).
floor_name(1, ground).
floor_name(2, first).
floor_name(3, second).

floor_distance(A, B, D) :- D is abs(A - B).

elevator_moves(Current, Target, Moves) :-
    ( Current < Target ->
        Num is Target - Current,
        findall(M, (between(1, Num, I), M is Current + I), Moves)
    ; Current > Target ->
        Num is Current - Target,
        findall(M, (between(1, Num, I), M is Current - I), Moves)
    ; Moves = []
    ).

%% ═══════════════════════════════════════════════════════════════════
%% VOTING
%% ═══════════════════════════════════════════════════════════════════

tally_votes(Votes, Total, Average) :-
    sum_list(Votes, Total),
    length(Votes, N),
    Average is Total / N.

consensus(Votes, Level) :-
    tally_votes(Votes, _, Avg),
    ( Avg >= 2.5 -> Level = strong_pass
    ; Avg >= 1.5 -> Level = pass
    ; Avg >= 0.5 -> Level = fail
    ;              Level = strong_fail
    ).

has_veto(Votes) :- member(0, Votes).

%% ═══════════════════════════════════════════════════════════════════
%% COMBINATION LOCK
%% ═══════════════════════════════════════════════════════════════════

combo_distance([], [], 0).
combo_distance([C|Cs], [G|Gs], D) :-
    combo_distance(Cs, Gs, D0),
    D is D0 + abs(C - G).

hint_from_distance(0, exact).
hint_from_distance(D, very_close) :- D > 0, D =< 2.
hint_from_distance(D, warm)       :- D > 2, D =< 4.
hint_from_distance(D, cold)       :- D > 4.

%% ═══════════════════════════════════════════════════════════════════
%% COLOR MIXER
%% ═══════════════════════════════════════════════════════════════════

mix_colors(R1, G1, B1, R2, G2, B2, Rm, Gm, Bm) :-
    Rm is (R1 + R2) // 2,
    Gm is (G1 + G2) // 2,
    Bm is (B1 + B2) // 2.

blend_channel(F, B, Alpha, R) :-
    R is (F * Alpha + B * (3 - Alpha)) // 3.

invert_color(R, G, B, Ri, Gi, Bi) :-
    notq(R, Ri), notq(G, Gi), notq(B, Bi).

qrgb_to_hex(R, G, B, Hex) :-
    R8 is R * 85, G8 is G * 85, B8 is B * 85,
    format(atom(Hex), '#~|~`0t~2R~|~`0t~2R~|~`0t~2R', [R8, G8, B8]).

%% ═══════════════════════════════════════════════════════════════════
%% 7-SEGMENT DISPLAY
%% ═══════════════════════════════════════════════════════════════════

seg7(0, [1,1,1,1,1,1,0]).
seg7(1, [0,1,1,0,0,0,0]).
seg7(2, [1,1,0,1,1,0,1]).
seg7(3, [1,1,1,1,0,0,1]).

%% ═══════════════════════════════════════════════════════════════════
%% ARITHMETIC
%% ═══════════════════════════════════════════════════════════════════

qfa(A, B, Cin, Sum, Cout) :-
    Total is A + B + Cin,
    Sum is Total mod 4,
    Cout is Total // 4.

qfs(A, B, Bin, Diff, Bout) :-
    Total is A - B - Bin,
    ( Total >= 0 -> Diff = Total, Bout = 0
    ;               Diff is Total + 4, Bout = 1
    ).

qmul1(A, B, Hi, Lo) :-
    Prod is A * B,
    Hi is Prod // 4,
    Lo is Prod mod 4.