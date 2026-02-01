// Parameters
$fn = 60;          // Smoothness
size = 20;         // Scale
puffy = 1.0;       // Thickness scale

module puffy_half() {
    hull() {
        // Top lobe of this half
        translate([size/2.5, size/2, 0]) 
            sphere(d=size);
            
        // The bottom tip (shared by both halves)
        translate([0, -size/2, 0]) 
            sphere(d=size/10);
            
        // Center meeting point (the "dip" starts here)
        translate([0, size/3, 0]) 
            sphere(d=size/1.1);
    }
}

difference(){
scale([1, 1, puffy]) {
    union() {
        puffy_half();             // Left side
        mirror([1, 0, 0])        // Flip for the right side
            puffy_half();
    }
}
translate([0,0,-(size*2.5)/2])cube(size*2.5, center=true);
}