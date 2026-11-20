cmake_minimum_required(VERSION 3.20)
project(pharmatrace_index_bench CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG")

# Third-party sources are cloned at fixed commits by the Dockerfile.
set(THIRD_PARTY "${CMAKE_CURRENT_SOURCE_DIR}/third_party" CACHE PATH "ALEX and tlx checkouts")
add_subdirectory(${THIRD_PARTY}/tlx tlx EXCLUDE_FROM_ALL)

add_executable(bench src/bench.cpp)
target_include_directories(bench PRIVATE ${THIRD_PARTY}/alex/src/core)
target_link_libraries(bench PRIVATE tlx)
# ALEX headers trigger many warnings under -Wall; keep the build output readable
target_compile_options(bench PRIVATE -w)
