double latOffset;
double longOffset;
double longScale;
const int latToMeter = 111318; //Conversion factor from latitude/longitude to meters

int idx = 0;

// mock lat/long values
double lats[] = {42.4440353, 42.445512, 42.445676, 42.443633};
double longs[] = {76.4841756, 76.482017, 76.484584, 76.484970};

// mock wind direction values
double dirs[] = {133.2, 144.3, 122.6, 111.3};

// mock imu values
double pitch[] = {5.3, 4.2, 3.2, 4.4};
double roll[] = {4.3, 2.2, 1.1, 3.9};
double yaw[] = {270.3, 199.0, 180.3, 280.3};


#ifndef coordinate_h
#define coordinate_h

typedef struct coord_t {
  double latitude; // float latitude
  double longitude; // float longitudes
}coord_t;
#endif

#ifndef coord_xy_h
#define coord_xy_h
typedef struct _coord_xy {
  double x; // float x coord
  double y; // float y coord
} coord_xy;
#endif

coord_xy origin;

/*Converts coordinate in latitude and longitude to xy*/
coord_xy xyPoint(coord_t latlong){
  double x = (latlong.longitude - longOffset) * longScale * latToMeter;
  double y = (latlong.latitude - latOffset) * latToMeter;
  return coord_xy({x, y});
}

void setOrigin(coord_t startPoint){
  origin = coord_xy({(double) 0, (double) 0});
  longOffset = startPoint.longitude; //used to generate X coordinate
  latOffset = startPoint.latitude; //used to generate Y coodinate
  longScale = cos(latOffset * M_PI/180);  //scaling factor to account for changing distance between longitude lines
}

coord_xy getRandPoint() {
  double x = (double) random(-100, 100) + (double) random(0, 100) / 100.0;
  double y = (double) random(-100, 100) + (double) random(0, 100) / 100.0;
  return coord_xy({x, y});
}

double getRandWindDirectionOrYaw() {
  return (double) random(0, 359) + (double) random(0, 100) / 100.0;
}

double getRandPitchOrRoll() {
  int ang = (((int) random(0, 20)) - 10) % 360;
  return (double) ang + (double) random(0, 100) / 100.0;
}

void setup() {
  Serial.begin(9600);
  Serial.print("Beginning Setup");
  randomSeed(analogRead(0));
}

void loop() {
  delay(2500);

  coord_xy currentPosition = getRandPoint();
  double windDir = getRandWindDirectionOrYaw();
  double pitch = getRandPitchOrRoll();
  double roll = getRandPitchOrRoll();
  double yaw = getRandWindDirectionOrYaw();
  
  Serial.print("----------NAVIGATION----------");
  Serial.print("\n");
  Serial.print("X position: "); 
  Serial.println(currentPosition.x,10);
  Serial.print("\n");
  Serial.print("Y position: "); 
  Serial.println(currentPosition.y,10);
  Serial.print("\n");
  Serial.print("Wind Direction: ");
  Serial.println(windDir, 2);
  Serial.print("\n");
  Serial.print("Pitch: ");
  Serial.println(pitch);
  Serial.print("\n");
  Serial.print("Roll: ");
  Serial.println(roll);
  Serial.print("\n");
  Serial.print("Yaw: ");
  Serial.println(yaw);
  Serial.print("\n");
  Serial.print("----------END----------");
  Serial.print("\n");
}
