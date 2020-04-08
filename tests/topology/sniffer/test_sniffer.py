from __future__ import absolute_import
from unittest import TestCase

from topology.sniffer.sniffer import parse_packet

class TestParsePacket(TestCase):
    # Samples of IP packet communications
    RAW_TCP_PACKET = b'\\\x93\xa2\xf4\xf7\xf6\xf0\x9f\xc2\x18\xa2\xdf\x08\x00E\x00\x004x\x98@\x00:\x06\x84Yh\x10\x19\xeb\xc0\xa8\x01/\x01\xbb\xb0\xf0v\xb1j.\xc2^L\xe3\x80\x10\x00 t\x99\x00\x00\x01\x01\x05\n\xc2^L\xc3\xc2^L\xe3'
    RES_TCP_PACKET = {'dest': '192.168.1.47', 'src': '104.16.25.235', 'version': '4', 'ip_header_length': '5', 'ttl': '58', 'transport': { 'src_port': '443', 'ack': '3260959971', 'dest_port': '45296', 'seq': '1991338542'}, 'transport_type': 'TCP'}

    RAW_UDP_PACKET = b'\xff\xff\xff\xff\xff\xff\\\x93\xa2\xf4\xf7\xf6\x08\x00E\x00\x00H\xdaT@\x00@\x11\xdb\xd1\xc0\xa8\x01/\xc0\xa8\x01\xff\xe1\x15\xe1\x15\x004\x82\xf3SpotUdp0,\xeb\xd8\x8b\xc1D@i\x00\x01\x00\x04H\x95\xc2\x03~\x8f\x95m\xb3\x82EaQ\xf8il\xdf|\xfd\xad\xc3H2\xf2'
    RES_UDP_PACKET = {'src': '192.168.1.47', 'dest': '192.168.1.255', 'ttl': '64', 'version': '4', 'transport_type': 'UDP', 'transport': {'length': '52', 'checksum': '33523', 'dest_port': '57621', 'src_port': '57621'}, 'ip_header_length': '5'}

    RAW_ICMP_PACKET = b'\\\x93\xa2\xf4\xf7\xf6\xf0\x9f\xc2\x18\xa2\xdf\x08\x00E\x00\x00T\x00\x00\x00\x007\x01\x1di\xd8:\xcc.\xc0\xa8\x01/\x00\x00\xf1\xf7*\x8b\x00\x13\xb1\xca\x00Z\x00\x00\x00\x00rr\x00\x00\x00\x00\x00\x00\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./01234567'
    RES_ICMP_PACKET = {'src': '216.58.204.46', 'dest': '192.168.1.47', 'ttl': '55', 'version': '4', 'transport_type': 'ICMP', 'transport': {'type': '0', 'checksum': '61943', 'code': '0'}, 'ip_header_length': '5'}

    RAW_OTHER_PACKET = b'\\\x93\xa2\xf4\xf2\xf4\xf0\x9e\xc2\x12\xa2\x1f\x08\x00E\x00\x004x\198@\x00:\x06\x84Yh\x10\x19\xeb\xc1\xa8\x01/\x01\xbb\xb0\xf0v\xb1j.\xc2^L\xe3\x80\x10\x00 t\x99\x00\x00\x01\x01\x05\n\xc2^L\xc3\xc2^L\xe3'
    RES_OTHER_PACKET = {'src': '132.89.104.16', 'ttl': '64', 'ip_header_length': '5', 'dest': '25.235.193.168', 'version': '4', 'transport_type': 'other'}

    # Unexpected binary after communication type \x11s
    BAD_FORM_PACKET = b'\\\x93\xa2\xf4\xf2\xf4\xf0\x9f\xc2\x12\xa1\x1f\x08\x11sF\x00\x004x\198@\x10:\x06\x84Yh\x10\x19\xeb\xc1\xa8\x01/\x01\xbb\xb0\xf0v\xb1j.\xc2^L\xe3\x80\x10\x00 t\x99\x00\x00\x01\x01\x05\n\xc2^L\xc3\xc2^L\xe3'

    # Unexpected beginning of packet
    BAD_BEGIN_PACKET = b'sarmale\\\x93\xa2\xf4\xf7\xf6\xf0\x9f\xc2\x18\xa2\xdf\x08\x00E\x00\x004x\x98@\x00:\x06\x84Yh\x10\x19\xeb\xc0\xa8\x01/\x01\xbb\xb0\xf0v\xb1j.\xc2^L\xe3\x80\x10\x00 t\x99\x00\x00\x01\x01\x05\n\xc2^L\xc3\xc2^L\xe3'

    # Packet with fields eliminated off
    BAD_LEN_PACKET = b'\\\x93\xf6\xf0\x9f\xc2\x18\xa2\x01/\x01\xbb\xb0\xf0v\xb1j.\xc2^L\xe3\x80\x10\x00 t\n\xc2^L\xc3\xc2^L\xe3'

    # Packet with modified payload
    BAD_PAYLOAD_PACKET = b'\\\x93\xa2\xf4\xf7\xf6\xf0\x9f\xc2\x18\xa2\x4f\x08\x00E\x00\x004x\x98@\x00:\x06\x84Yh\x10\x19\xeb\xc0\xa8\x01/\x01\xbb\xb0\xf0v\xb1j.\xc2^L\xe3\x80\x10\x00 t\x99\x00\x00\x01\x01\x02\n\xc2^L\xc3\xc2^L\xe3'

    # Non-IP good-formatted packets
    GOOD_PACKETS_USELESS = [
        b"\xff\xff\xff\xff\xff\xffx\xbd\xbc\xdf\xa9\x8f\x08\x06\x00\x01\x08\x00\x06\x04\x00\x01x\xbd\xbc\xdf\xa9\x8f\xc0\xa8\x01'\x00\x00\x00\x00\x00\x00\xc0\xa8\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b'\xff\xff\xff\xff\xff\xff@\xb8\x9ar\xb9\x9b\x08\x06\x00\x01\x08\x00\x06\x04\x00\x01@\xb8\x9ar\xb9\x9b\xc0\xa8\x01\x81\x00\x00\x00\x00\x00\x00\xc0\xa8\x01g\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        b'\xff\xff\xff\xff\xff\xff@\xb8\x9ar\xb9\x9b\x08\x06\x00\x01\x08\x00\x06\x04\x00\x01@\xb8\x9ar\xb9\x9b\xc0\xa8\x01\x81\x00\x00\x00\x00\x00\x00\xc0\xa8\x01o\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        b'\xff\xff\xff\xff\xff\xff@\xb8\x9ar\xb9\x9b\x08\x06\x00\x01\x08\x00\x06\x04\x00\x01@\xb8\x9ar\xb9\x9b\xc0\xa8\x01\x81\x00\x00\x00\x00\x00\x00\xc0\xa8\x01\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        b'\xff\xff\xff\xff\xff\xff\xf0\x9f\xc2\x18\xa2\xdf\x08\x06\x00\x01\x08\x00\x06\x04\x00\x01\xf0\x9f\xc2\x18\xa2\xdf\xc0\xa8\x01\x01\x00\x00\x00\x00\x00\x00\xc0\xa8\x01\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    ]

    def check_packet(self, raw_packet, res_packet):
        packet = parse_packet(raw_packet)
        self.assertDictEqual(packet, res_packet)

    def test_tcp_packet(self): self.check_packet(self.RAW_TCP_PACKET, self.RES_TCP_PACKET)
    def test_udp_packet(self): self.check_packet(self.RAW_UDP_PACKET, self.RES_UDP_PACKET)
    def test_icmp_packet(self): self.check_packet(self.RAW_ICMP_PACKET, self.RES_ICMP_PACKET)
    def test_other_packet(self): self.check_packet(self.RAW_OTHER_PACKET, self.RES_OTHER_PACKET)

    def test_useless_packets_ignored(self):
        self.assertTrue(
            all([parse_packet(p) is None for p in self.GOOD_PACKETS_USELESS]),
            msg="Useless packet parsed.")

    def test_bad_begin_packet(self):
        self.assertIsNone(parse_packet(self.BAD_FORM_PACKET))

    def test_bad_formatted_packet(self):
        self.assertIsNone(parse_packet(self.BAD_FORM_PACKET))

    def test_bad_length_packet(self):
        self.assertIsNone(parse_packet(self.BAD_LEN_PACKET))

    def test_bad_paylad_doesnt_affect_parsing(self):
        self.check_packet(self.BAD_PAYLOAD_PACKET, self.RES_TCP_PACKET)
