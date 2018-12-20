from typing import Dict, List

from connections.sub_connection import SubConnection
from utils.utils import SourceIp


class IpLinkerEntry(object):
    def __init__(self):
        self.initial_sub_connections: List[float] = []
        self.non_initial_sub_connections_number = 0
        self.start_time = float('inf')
        self.end_time = 0
        self.is_linked = False
        self.connections_numbers: List[int] = []
        self.removed_initial_sub_connections: List[float] = []

    def add_sub_connection(self, sub_connection):
        if sub_connection.is_initial is True:
            self.initial_sub_connections.append(sub_connection.start_time)
        else:
            self.non_initial_sub_connections_number += 1
        self.start_time = min(self.start_time, sub_connection.start_time)
        self.end_time = max(self.end_time, sub_connection.end_time)
        self.connections_numbers.append(sub_connection.of_connection_num)

    def remove_initial_sub_connections_after_time(self, time, connection_time):
        tmp_initial_sub_connections = []
        for start_time in self.initial_sub_connections:
            if start_time + connection_time >= time:
                tmp_initial_sub_connections.append(start_time)
            else:
                self.removed_initial_sub_connections.append(start_time)
        self.initial_sub_connections = tmp_initial_sub_connections


class IpsLinker:
    def __init__(self):
        self.__ip_linker_map: Dict[SourceIp, IpLinkerEntry] = {}

    def add_sub_connection(self, sub_connection: SubConnection):
        entry = self.__ip_linker_map.get(sub_connection.source_ip)
        if entry is None:
            entry = IpLinkerEntry()
            self.__ip_linker_map[sub_connection.source_ip] = entry
        entry.add_sub_connection(sub_connection)

    def add_sub_connections(self, sub_connections: List[SubConnection]):
        for sub_connection in sub_connections:
            self.add_sub_connection(sub_connection)

    def __find_potential_linked_records(self, record, transaction_log, connection_time, should_remove_expired):
        potential_records = []
        record_data = record[1]
        for i in range(0, len(transaction_log)):
            potential_record_data = transaction_log[i][1]
            if record_data.start_time <= potential_record_data.start_time:
                break
            if should_remove_expired:
                potential_record_data.remove_initial_sub_connections_after_time(record_data.start_time, connection_time)
            if not potential_record_data.is_linked and \
                    potential_record_data.end_time < record_data.start_time and \
                    record_data.non_initial_sub_connections_number <= len(potential_record_data.initial_sub_connections):
                potential_records.append(transaction_log[i])
        return potential_records

    def try_to_link_ips(self, connection_time):
        transaction_log = list(self.__ip_linker_map.items())
        transaction_log.sort(key=lambda r: r[1].start_time)
        for record in transaction_log:
            transaction_data: IpLinkerEntry = record[1]
            if transaction_data.non_initial_sub_connections_number != 0:
                potential_linked_records = self.__find_potential_linked_records(record, transaction_log,
                                                                                connection_time, False)
                if len(potential_linked_records) > 1:
                    potential_linked_records = self.__find_potential_linked_records(record, transaction_log,
                                                                                    connection_time, True)
                if len(potential_linked_records) != 1:
                    # print(str(potential_linked_records))
                    return 0
                potential_linked_records[0][1].is_linked = True
                transaction_data.initial_sub_connections.extend(potential_linked_records[0][1].initial_sub_connections)
        return 1
