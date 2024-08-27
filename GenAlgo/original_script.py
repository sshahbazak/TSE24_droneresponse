from Fuzz import FuzzTestor as ft
# import threading
# import signal
# import os
# import sys
# # def run_fuzz_test():
# #     fuzz_testor = ft.Fuzz_Testor()
# #     fuzz_test = ft.Fuzz_Test(drone_id="Polkadot",
# #                              modes=['OFFBOARD'],
# #                              geofence=[3],
# #                              throttle=[3])
# #     print('[Debug] Printing return value ' +str(fuzz_test))
# #     fuzz_testor.run_test(fuzz_test)

# # if __name__ == "__main__":
# #     try:
# #         run_fuzz_test()
# #     except SystemExit as e:
# #         print('Caught SystemExit with code - ')

# '''
# Functions below gracefully shutdown all running processes and threads.
# signal_handler - recieves interrupt and shutdowns rospy, docker, and timer
# shutdown_timer - sets events to exit timer thread
# '''
# def trigger_shutdown():
#     os.kill(os.getpid(), signal.SIGINT)

# fuzz_testor = ft.Fuzz_Testor()
# signal.signal(signal.SIGINT, fuzz_testor.signal_handler)


# fuzz_test1 = ft.Fuzz_Test(drone_id="Polkadot",
# modes=['OFFBOARD'],
# # states=['BriarWaypoint2'],
# geofence=[3],
# throttle=[3]
# )

# main_thread1 = threading.Thread(target=fuzz_testor.run_test, args=(fuzz_test1, ))
# main_thread1.start()
# fuzz_testor.run_test(fuzz_test1)

# fuzz_testor.completion_event.wait()
# main_thread1.join()
# # trigger_shutdown()
# print("1st Fuzz testing completed. Now running 2nd")


# fuzz_testor.completion_event.clear()
# fuzz_test2 = ft.Fuzz_Test(drone_id="Polkadot",
# geofence=[5],
# throttle=[3]
# )

# main_thread = threading.Thread(target=fuzz_testor.run_test, args=(fuzz_test2, ))
# main_thread.start()
# fuzz_testor.run_test(fuzz_test2)

# fuzz_testor.completion_event.wait()


# print('Shutting Down everything')
# trigger_shutdown()
# sys.exit(0)
