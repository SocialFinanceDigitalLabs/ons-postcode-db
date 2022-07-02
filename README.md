# Binary Postcode Format


Outcode - 20 bits

C1 - 5 bits
C2 - 5 bits - NIL omitted
C3 - 5 bits - NIL omitted
C4 - 5 bits - NIL omitted

Incode - 14 bits

D - 4 bits
C1 - 5 bits
C2 - 5 bits

7 bits for signalling

# Reference Values

Country - 6 (3 bits)
County - 30 (5 bits)
Urban/Rural - 19 (5 bits)
Electoral Division - 1579 (11 bits)
LAs - 376 (9 bits)

ED + LA (11 bits + mapping)

Electoral + LAs < 2000

1 bits - 0-1 (2) = 0x01
2 bits - 0-3 (4) = 0x03
3 bits - 0-7 (8) = 0x07
4 bits - 0-15 (16) = 0x0F
5 bits - 0-31 (32) = 0x1F
6 bits - 0-63 (64) = 0x3F
7 bits - 0-127 (128) = 0x7F
8 bits - 0-255 (256) = 0xFF
9 bits - 0-511 (512) = 0x1FF
10 bits - 0-1023 (1024) = 0x3FF
11 bits - 0-2047 (2048) = 0x7FF
12 bits - 0-4095 (4096) = 0xFFF
13 bits - 0-8191 (8192) = 0x1FFF
14 bits - 0-16383 (16384) = 0x3FFF
15 bits - 0-32767 (32768) = 0x7FFF
16 bits - 0-65535 (65536) = 0xFFFF
17 bits - 0-131071 (131072) = 0x1FFFF
18 bits - 0-262143 (262144) = 0x3FFFF
19 bits - 0-524287 (524288) = 0x7FFFF
20 bits - 0-1048575 (1048576) = 0xFFFFF
22 bits - 0-2097151 (2097152) = 0x1FFFFF
24 bits - 0-4194303 (4194304) = 0x3FFFFF

There are only 1799 unique combinations of the location
fields, so these can easily be in a mapping table.

Largest outcode lat/lon variance is 2.195249 degrees

Stored as an integer, that's 2,195,249 requiring 3 bytes. 

Whereas for the whole dataset, the range is

Lat: 49.891974 - 60.800694 = -10.90872
Lon: -8.163139 - 1.762773 = 9.925911

So 10,908,720 - requiring significantly more space. 

However, these coordinates are very precise with a resolution
in the order of 10cm - this is way more precision than we, which
is to calculate the difference between two postcodes. 

Reducing the precision to 4 decimal places gives us a resolution 
in the order of 10m which is enough for this purpose, even in 
densely populated areas.

That gives us a range of 0-109087 for latitude, and 0-92591 for
longitude, requiring 17 bits each, or 34 bits combined. 

If we compute the centroids for each locations, we get the largest
deviation from the original coordinates of 39000 points which we
can store in 16 bits, thus making the total 32 bits for location.
Don't know if this is signficant enough to warrant. 


