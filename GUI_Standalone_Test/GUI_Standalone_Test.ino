double latOffset;
double longOffset;
double longScale;
const int latToMeter = 111318; //Conversion factor from latitude/longitude to meters

// mock lat/long values
double lats[] = {42.4440353, 42.445512, 42.445676, 42.443633};
double longs[] = {76.4841756, 76.482017, 76.484584, 76.484970};
int idx = 0;

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

void setup() {
  Serial.begin(9600);
  Serial.print("Beginning Setup");
  coord_t latlong = {lats[0],longs[0]};
  setOrigin(latlong);
}

void loop() {
  delay(2500);

  idx++;
  idx = idx % 4;
  
  coord_t coord_lat_lon = {lats[idx], longs[idx]};
  coord_xy currentPosition = xyPoint(coord_lat_lon);
  
  Serial.print("----------NAVIGATION----------");
  Serial.print("\n");
  Serial.print("X position: "); 
  Serial.println(currentPosition.x,10);
  Serial.print("\n");
  Serial.print("Y position: "); 
  Serial.println(currentPosition.y,10);
  Serial.print("\n");
  Serial.print("----------END----------");
  Serial.print("\n");
}
