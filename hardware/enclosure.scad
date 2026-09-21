// DIY Sync Box enclosure - parametric OpenSCAD model
// Render: openscad -o base.stl -D 'part="base"' enclosure.scad
//         openscad -o lid.stl  -D 'part="lid"'  enclosure.scad
// All dimensions in mm. Internal component sizes marked "MEASURE" are placeholders
// taken from vendor drawings or estimates; measure your parts before printing.

part = "base";          // "base" | "lid" | "both"
wall = 2.5;
inner_l = 250;          // X, left-right (front face is the long side, y = 0)
inner_w = 170;          // Y, front-back
inner_h = 46;           // Z, internal height (LRS-100-5 is 30 mm, Pi 5 + cooler ~ 22 mm)
corner_r = 4;
lid_lip = 3;
screw_d = 3.2;          // M3 lid screws into heat-set inserts at the corners
insert_d = 4.0;

// ---- component footprints (x, y of front-left corner; l, w) ---------------
psu     = [ 8, 65, 129, 97 ];   // Mean Well LRS-100-5, 129 x 97 x 30 (datasheet)
pi5     = [ 155, 100, 85, 56 ]; // Raspberry Pi 5, ports facing +X (right wall)
hdmi_u  = [ 145, 8, 100, 65 ];  // EZCOO EZ-SP12H2 -- MEASURE, estimate 100 x 65 x 22
grabber = [ 75, 8, 65, 25 ];    // MS2130 dongle -- MEASURE, estimate 65 x 25 x 13
pico    = [ 8, 8, 51, 21 ];     // Raspberry Pi Pico 51 x 21
shifter = [ 8, 35, 30, 20 ];    // 74AHCT125 on a small proto board

// Pi 5 mounting holes (from the Pi 5 mechanical drawing): 58 x 49 mm, 3.5 mm from edges
pi_holes = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];
// LRS-100-5 bottom holes (datasheet): 4 x M3 on a 116 x 84 grid -- verify against your datasheet revision
psu_holes = [[6.5, 6.5], [122.5, 6.5], [6.5, 90.5], [122.5, 90.5]];

// ---- front panel cutouts, positioned along X, centred on Z --------------
// HDMI panel cable flange: 25 x 13 opening, screws 30 mm apart (StarTech/Qaoquda style) -- MEASURE
hdmi_cut = [25, 13];
hdmi_screw_pitch = 30;
front_items = [
    // [x_centre, type]
    [ 30,  "iec"   ],   // IEC C14 fused inlet, opening 27.5 x 47.5 (rotated to lie flat: 47.5 wide x 27.5 high), screws 40 mm
    [ 95,  "hdmi"  ],   // HDMI IN 1
    [ 135, "hdmi"  ],   // HDMI IN 2 (optional, blank if single-source)
    [ 175, "hdmi"  ],   // HDMI OUT
    [ 215, "gx16"  ],   // LED lead, GX16-4, 16 mm hole
    [ 240, "led"   ],   // 5 mm status LED
];

outer_l = inner_l + 2 * wall;
outer_w = inner_w + 2 * wall;
outer_h = inner_h + wall;

module rounded_box(l, w, h, r) {
    hull() for (x = [r, l - r], y = [r, w - r]) translate([x, y, 0]) cylinder(r = r, h = h, $fn = 32);
}

module standoff(h = 5, d = 6, hole = 2.5) {
    difference() { cylinder(d = d, h = h, $fn = 24); cylinder(d = hole, h = h + 1, $fn = 16); }
}

module front_cutouts() {
    // cut through the front wall (y from -1 to wall+1), centred at z = inner_h/2 + wall
    zc = wall + inner_h / 2;
    for (it = front_items) {
        x = wall + it[0];
        t = it[1];
        translate([x, -1, zc]) rotate([-90, 0, 0]) {
            if (t == "hdmi") {
                translate([-hdmi_cut[0]/2, -hdmi_cut[1]/2, 0]) cube([hdmi_cut[0], hdmi_cut[1], wall + 2]);
                for (sx = [-1, 1]) translate([sx * hdmi_screw_pitch / 2, 0, 0]) cylinder(d = 3.2, h = wall + 2, $fn = 16);
            } else if (t == "iec") {
                translate([-47.5/2, -27.5/2, 0]) cube([47.5, 27.5, wall + 2]);
                for (sx = [-1, 1]) translate([sx * 40 / 2, 0, 0]) cylinder(d = 3.2, h = wall + 2, $fn = 16);
            } else if (t == "gx16") {
                cylinder(d = 16.2, h = wall + 2, $fn = 48);
            } else if (t == "led") {
                cylinder(d = 5.2, h = wall + 2, $fn = 24);
            }
        }
    }
}

module vent_slots(x0, y0, count, len, pitch = 4, slot = 1.8) {
    for (i = [0 : count - 1]) translate([x0 + i * pitch, y0, -1]) cube([slot, len, wall + 2]);
}

module base() {
    difference() {
        rounded_box(outer_l, outer_w, outer_h, corner_r);
        translate([wall, wall, wall]) cube([inner_l, inner_w, inner_h + 1]);
        front_cutouts();
        // right wall: Pi 5 USB / Ethernet service opening (2 x USB3 + 2 x USB2 + RJ45 ~ 60 x 18)
        translate([outer_l - wall - 1, wall + pi5[1] + 2, wall + 4]) cube([wall + 2, 60, 18]);
        // floor vents under the Pi and the PSU
        translate([0, 0, 0]) {
            vent_slots(wall + pi5[0] + 5, wall + pi5[1] + 5, 16, pi5[3] - 10);
            vent_slots(wall + psu[0] + 5, wall + psu[1] + 5, 28, psu[3] - 10);
        }
        // rear wall vents
        for (i = [0 : 30]) translate([wall + 10 + i * 7, outer_w - wall - 1, wall + 8]) cube([3, wall + 2, inner_h - 16]);
    }
    // standoffs
    for (h = pi_holes) translate([wall + pi5[0] + h[0], wall + pi5[1] + h[1], wall]) standoff(h = 5);
    for (h = psu_holes) translate([wall + psu[0] + h[0], wall + psu[1] + h[1], wall]) standoff(h = 4, d = 8, hole = 3.2);
    // lid screw posts with heat-set insert holes at the corners
    for (x = [wall + 5, outer_l - wall - 5], y = [wall + 5, outer_w - wall - 5])
        translate([x, y, wall]) difference() { cylinder(d = 9, h = inner_h, $fn = 24); cylinder(d = insert_d, h = inner_h + 1, $fn = 16); }
}

module lid() {
    difference() {
        union() {
            rounded_box(outer_l, outer_w, wall, corner_r);
            translate([wall + 0.3, wall + 0.3, wall]) difference() {
                cube([inner_l - 0.6, inner_w - 0.6, lid_lip]);
                translate([wall, wall, -1]) cube([inner_l - 0.6 - 2 * wall, inner_w - 0.6 - 2 * wall, lid_lip + 2]);
            }
        }
        for (x = [wall + 5, outer_l - wall - 5], y = [wall + 5, outer_w - wall - 5])
            translate([x, y, -1]) cylinder(d = screw_d, h = wall + lid_lip + 2, $fn = 16);
        // top vents over the Pi (active cooler exhaust) and the PSU
        vent_slots(wall + pi5[0] + 5, wall + pi5[1] + 5, 18, pi5[3] - 10);
        vent_slots(wall + psu[0] + 5, wall + psu[1] + 5, 28, psu[3] - 10);
        // port labels (engraved 0.6 mm)
        labels = [[95, "IN 1"], [135, "IN 2"], [175, "OUT"], [215, "LED"], [30, "AC"]];
        for (l = labels) translate([wall + l[0], wall + 6, wall - 0.6]) linear_extrude(1) text(l[1], size = 5, halign = "center");
    }
}

if (part == "base" || part == "both") base();
if (part == "lid") lid();
if (part == "both") translate([0, outer_w + 15, 0]) lid();
