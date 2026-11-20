-- btree_gist lets an EXCLUDE constraint combine equality (sensor_id) with range overlap (assignment period).
CREATE EXTENSION IF NOT EXISTS btree_gist;
