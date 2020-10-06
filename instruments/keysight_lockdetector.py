from keysight_scope import LockDetector, scope_visa_addresses

lock_channels = {1: {'laser':'foo1','low_level':-500},
				 2: {'laser':'foo2','low_level':-500},
				 }

lockdetector = LockDetector(visa_address=scope_visa_addresses['near laser tables'],
							lock_channels=lock_channels)

if __name__ == '__main__':
	lockdetector.main()