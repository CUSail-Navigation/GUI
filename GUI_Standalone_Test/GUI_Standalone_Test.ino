/**
 * Mocks the output of the Xbee module on the sailboat for use with testing the GUI
 */

int idx = 0; // number of times the output has been printed

// mock origin latitude and longitude
double origLat = 42.4440353;
double origLong = -76.4841756;

#ifndef coord_xy_h
#define coord_xy_h
typedef struct _coord_xy {
  double x; // float x coord
  double y; // float y coord
} coord_xy;
#endif

/* Generates a random (x, y) point */
coord_xy getRandPoint() {
  double x = (double) random(-100, 100) + (double) random(0, 100) / 100.0;
  double y = (double) random(-100, 100) + (double) random(0, 100) / 100.0;
  return coord_xy({x, y});
}

/* 
 *  Generates a random angle within 0-360 degrees
 *  Use for wind direction, yaw, heading, and servo angles
 */
double getRand360() {
  return (double) random(0, 359) + (double) random(0, 100) / 100.0;
}

/*
 * Generates a random angle within -10-10 degrees
 * Use for pitch and roll
 */
double getRand20() {
  int ang = (((int) random(0, 20)) - 10) % 360;
  return (double) ang + (double) random(0, 100) / 100.0;
}

/*
 * Generates a random double between a and b
 */
double getRand(double a, double b) {
  return (double) random(a, b - 1) + (double) random(0, 100) / 100.0;
}

void setup() {
  Serial.begin(9600);
  Serial.print("Beginning Setup");
  Serial.print("\n");
  randomSeed(analogRead(0));
}

/* Print a random number of random waypoints */
void printAllWaypoints() {
  Serial.print("----------WAYPOINTS----------");
  
  int num = (int) random(5, 20);
  for (int i = 0; i < num; i++) {
    coord_xy waypt = getRandPoint();
    Serial.print(",X:");
    Serial.print(waypt.x, 4);
    Serial.print(" Y:");
    Serial.print(waypt.y, 4);
  }

  Serial.print(",----------END----------\n");
}

/* Print the hit a random waypoint message */
void printHitWaypoint() {
  Serial.print("----------HIT----------");
  
  coord_xy waypt = getRandPoint();
  Serial.print(",X:");
  Serial.print(waypt.x, 4);
  Serial.print(" Y:");
  Serial.print(waypt.y, 4);

  Serial.print(",----------END----------\n");
}

void loop() {
  delay(1000);

  if (idx % 20 == 0) {
    if (idx % 40 == 0) {
      printHitWaypoint();
    }
    printAllWaypoints();
    idx = 0;
  }
  idx++;

  coord_xy currentPosition = getRandPoint();
  double windDir = getRand360();
  double relWind = getRand360();
  double pitch = getRand20();
  double roll = getRand20();
  double yaw = getRand360();
  double sail = getRand(-90.0, 90.0);
  double tail = getRand(-30.0, 30.0);
  double heading = getRand360();
  double angVel = getRand(-2.0, 2.0);
  double xVel = getRand(-2.0, 2.0);
  double yVel = getRand(-2.0, 2.0);
  double xWay = getRand(-50.0, 50.0);
  double yWay = getRand(-50.0, 50.0);

  Serial.print("----------NAVIGATION----------");
  Serial.print(",Origin Latitude: ");
  Serial.print(origLat, 10);
  Serial.print(",Origin Longitude: ");
  Serial.print(origLong, 10);
  Serial.print(",X position: "); 
  Serial.print(currentPosition.x,3);
  Serial.print(",Y position: "); 
  Serial.print(currentPosition.y,3);
  Serial.print(",Wind Direction: ");
  Serial.print(windDir, 3);
  Serial.print(",Relative wind: ");
  Serial.print(relWind, 3);
  Serial.print(",Pitch: ");
  Serial.print(pitch);
  Serial.print(",Roll: ");
  Serial.print(roll);
  Serial.print(",Yaw: ");
  Serial.print(yaw);
  Serial.print(",Sail Angle: ");
  Serial.print(sail);
  Serial.print(",Tail Angle: ");
  Serial.print(tail);
  Serial.print(",Heading: ");
  Serial.print(heading);
  Serial.print(",Angular velocity: ");
  Serial.print(angVel, 3);
  Serial.print(",X velocity: ");
  Serial.print(xVel, 3);
  Serial.print(",Y velocity: ");
  Serial.print(yVel, 3);
  Serial.print(",X waypoint: ");
  Serial.print(xWay, 3);
  Serial.print(",Y waypoint: ");
  Serial.print(yWay, 3);
  Serial.print(",----------END----------\n");
}
