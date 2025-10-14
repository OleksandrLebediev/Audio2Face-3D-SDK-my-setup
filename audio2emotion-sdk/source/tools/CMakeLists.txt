add_executable(a2e_csv)

set_target_properties(a2e_csv PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY ${A2E_BINARY_DIR}/lib
    LIBRARY_OUTPUT_DIRECTORY ${A2E_BINARY_DIR}/lib
    RUNTIME_OUTPUT_DIRECTORY ${A2E_BINARY_DIR}/bin
)

target_sources(a2e_csv PRIVATE
    a2e_csv.cpp
)

target_link_libraries(a2e_csv PRIVATE
    audio2x
    AudioFile::AudioFile
    cxxopts::cxxopts
)


