add_executable(a2f_weights_csv)

set_target_properties(a2f_weights_csv PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/lib
    LIBRARY_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/lib
    RUNTIME_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/bin
)

target_sources(a2f_weights_csv PRIVATE
    a2f_weights_csv.cpp
)

target_link_libraries(a2f_weights_csv PRIVATE
    audio2face-core
    audio2x-common
    CXXOPTS::cxxopts
    AudioFile::AudioFile
)

add_executable(a2f_a2e_combined_csv)

set_target_properties(a2f_a2e_combined_csv PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/lib
    LIBRARY_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/lib
    RUNTIME_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/bin
)

target_sources(a2f_a2e_combined_csv PRIVATE
    a2f_a2e_combined_csv.cpp
)

target_link_libraries(a2f_a2e_combined_csv PRIVATE
    audio2face-core
    audio2emotion-core
    audio2x-common
    CXXOPTS::cxxopts
    AudioFile::AudioFile
)

add_executable(a2f_geometry_npz)

set_target_properties(a2f_geometry_npz PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/lib
    LIBRARY_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/lib
    RUNTIME_OUTPUT_DIRECTORY ${A2F_BINARY_DIR}/bin
)

target_sources(a2f_geometry_npz PRIVATE
    a2f_geometry_npz.cpp
)

target_link_libraries(a2f_geometry_npz PRIVATE
    audio2face-core
    audio2x-common
    CXXOPTS::cxxopts
    AudioFile::AudioFile
    Cnpy::Cnpy
)


