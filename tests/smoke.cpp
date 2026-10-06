// Checks that the Aravis files arranged for 3rdpartypublic are complete.
//
// The workflow compiles this against the arranged headers alone, links it
// against the arranged static libraries alone, checks that the result loads
// nothing but Windows DLLs, and runs it. It then grabs one frame from
// Aravis's built-in fake camera, which needs no hardware and no network but
// still exercises GLib, GObject, GIO and the GenICam parser.

#include <arv.h>

#include <cstdio>

int main()
{
    std::printf("Aravis %u.%u.%u\n", arv_get_major_version(),
                arv_get_minor_version(), arv_get_micro_version());

    arv_enable_interface("Fake");
    arv_update_device_list();
    const unsigned int n_devices = arv_get_n_devices();
    std::printf("%u device(s) found:\n", n_devices);
    for (unsigned int i = 0; i < n_devices; i++)
        std::printf("  %s\n", arv_get_device_id(i));

    GError* error = nullptr;
    ArvCamera* camera = arv_camera_new("Fake_1", &error);
    if (camera == nullptr) {
        std::fprintf(stderr, "Could not open the fake camera: %s\n",
                     error != nullptr ? error->message : "unknown error");
        g_clear_error(&error);
        arv_shutdown();
        return 1;
    }

    int result = 1;
    const guint64 timeout_us = 2000000;
    ArvBuffer* buffer = arv_camera_acquisition(camera, timeout_us, &error);
    if (buffer == nullptr) {
        std::fprintf(stderr, "Acquisition failed: %s\n",
                     error != nullptr ? error->message : "unknown error");
        g_clear_error(&error);
    } else if (arv_buffer_get_status(buffer) != ARV_BUFFER_STATUS_SUCCESS) {
        std::fprintf(stderr, "Acquisition returned buffer status %d\n",
                     static_cast<int>(arv_buffer_get_status(buffer)));
    } else {
        std::printf("Acquired a %d x %d frame from the fake camera\n",
                    arv_buffer_get_image_width(buffer),
                    arv_buffer_get_image_height(buffer));
        result = 0;
    }

    if (buffer != nullptr)
        g_object_unref(buffer);
    g_object_unref(camera);
    arv_shutdown();
    return result;
}
