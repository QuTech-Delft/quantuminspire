# Quantum Inspire SDK
#
# Copyright 2022 QuTech Delft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
from functools import partial
from json import JSONDecoder, JSONEncoder
from typing import Any, Callable, Dict, Tuple, Optional, List, Union
from dataclasses_json.api import DataClassJsonMixin

import numpy as np
import numpy.typing as npt


EncodedNumpyArray = Dict[str, Union[str, Dict[str, Union[str, List[Any], bytes]]]]

# type alias for numpy.ndarray
numpy_ndarray_type = npt.NDArray[Any]

# A callable type for transforming a given argument with a type to another type
TransformFunctionResult = Any
TransformFunction = Callable[[Any], TransformFunctionResult]


class NumpyKeys:
    """The custom values types for encoding and decoding numpy arrays."""
    OBJECT: str = '__object__'
    CONTENT: str = '__content__'
    DATA_TYPE: str = '__data_type__'
    SHAPE: str = '__shape__'
    ARRAY: str = '__ndarray__'


class NumpyArrayEncDec:
    """ Helper class for the numpy array decoder and encoder """
    @staticmethod
    def encode_numpy_array(
        array: Union[numpy_ndarray_type]) -> EncodedNumpyArray:
        """ Encode numpy array to store in database.
        Args:
            array: Numpy array to encode.

        Returns:
            The encoded array.

        """
        return {
            NumpyKeys.OBJECT: np.array.__name__,
            NumpyKeys.CONTENT: {
                NumpyKeys.ARRAY: base64.b64encode(array.tobytes()).decode('ascii'),
                NumpyKeys.DATA_TYPE: array.dtype.str,
                NumpyKeys.SHAPE: list(array.shape),
            }
        }

    @staticmethod
    def decode_numpy_array(encoded_array: Dict[str, Any]) -> numpy_ndarray_type:
        """ Decode a numpy array from database.

        Args:
            encoded_array: The encoded array to decode.

        Returns:
            The decoded array.
        """
        array: numpy_ndarray_type
        content = encoded_array[NumpyKeys.CONTENT]
        array = np.frombuffer(base64.b64decode(content[NumpyKeys.ARRAY]),
                              dtype=np.dtype(content[NumpyKeys.DATA_TYPE])).reshape(content[NumpyKeys.SHAPE])
        # recreate the array to make it writable
        array = np.array(array)

        return array


class JsonSerializeKey:
    """ The custom value types for the JSON serializer """
    OBJECT = '__object__'
    CONTENT = '__content__'


class Encoder(JSONEncoder):
    """ A JSON encoder """

    def __init__(self, **kwargs: Any) -> None:
        """ Constructs a JSON Encoder """
        super().__init__(**kwargs)
        # creates a new transform table
        self.encoders: Dict[type, TransformFunction] = {}

    def default(self, o: Any) -> TransformFunctionResult:
        if type(o) in self.encoders:
            return self.encoders[type(o)](o)

        return JSONEncoder.default(self, o)


class Decoder(JSONDecoder):
    """ A JSON decoder """

    def __init__(self) -> None:
        """ Constructs a JSON Decoder """
        super().__init__(object_hook=self._object_hook)
        # creates a new transform table
        self.decoders: Dict[str, TransformFunction] = {}

    def _object_hook(self, obj: Any) -> TransformFunctionResult:
        if isinstance(obj, dict):
            if JsonSerializeKey.OBJECT in obj:
                if obj[JsonSerializeKey.OBJECT] in self.decoders:
                    return self.decoders[obj[JsonSerializeKey.OBJECT]](obj)
                else:
                    raise ValueError(f'object key {obj[JsonSerializeKey.OBJECT]} not in decoders')

        return obj


def _encode_bytes(data: Any) -> Dict[str, Any]:
    return {JsonSerializeKey.OBJECT: bytes.__name__, JsonSerializeKey.CONTENT: data.decode('utf-8')}


def _decode_bytes(data: Dict[str, Any]) -> bytes:
    return bytes(data[JsonSerializeKey.CONTENT].encode('utf-8'))


def _encode_tuple(item: Tuple[Any, Any]) -> Dict[str, Any]:
    return {
        JsonSerializeKey.OBJECT: tuple.__name__,
        JsonSerializeKey.CONTENT: [serializer.encode_data(value) for value in item]
    }


def _decode_tuple(data: Dict[str, Any]) -> Tuple[Any, ...]:
    return tuple(data[JsonSerializeKey.CONTENT])


def _encode_numpy_number(item: Any) -> Dict[str, Any]:
    return {
        JsonSerializeKey.OBJECT: '__npnumber__',
        JsonSerializeKey.CONTENT: {
            '__npnumber__': base64.b64encode(item.tobytes()).decode('ascii'),
            '__data_type__': item.dtype.str,
        }
    }


def _decode_numpy_number(item: Dict[str, Any]) -> Any:
    obj = item[JsonSerializeKey.CONTENT]
    return np.frombuffer(base64.b64decode(obj['__npnumber__']), dtype=np.dtype(obj['__data_type__']))[0]


def _encode_dataclass(object_: DataClassJsonMixin, class_name: str) -> Dict[str, Any]:
    """ Encodes a JSON dataclass object

    Args:
        object_: Object to be encoded
        class_name: Object dataclass name

    Returns:
        Dictionary that can be serialized
    """
    return {JsonSerializeKey.OBJECT: class_name,
            JsonSerializeKey.CONTENT: object_.to_dict()}


def _decode_dataclass(data: Dict[str, Any], class_type: DataClassJsonMixin) -> TransformFunctionResult:
    """ Decodes a JSON dataclass object

    Args:
        data: Data to be decoded
        class_type: The dataclass type to decode

    Returns
        Object of specified class_type type with decoded data
    """
    return class_type.from_dict(data[JsonSerializeKey.CONTENT])


class Serializer:
    """ A general serializer to serialize data to JSON and vice versa. It allows
     extending the types with a custom encoder and decoder."""

    def __init__(self, encoders: Optional[Dict[type, TransformFunction]] = None,
                 decoders: Optional[Dict[str, TransformFunction]] = None):
        """ Creates a serializer

        Args:
            encoders: The default encoders if any
            decoders: The default decoders if any
        """

        self.encoder = Encoder()
        self.decoder = Decoder()

        if encoders is None:
            encoders = {}
        self.encoder.encoders = encoders
        if decoders is None:
            decoders = {}
        self.decoder.decoders = decoders

        self.register(bytes, _encode_bytes, bytes.__name__, _decode_bytes)
        self.register(np.ndarray, NumpyArrayEncDec.encode_numpy_array, np.array.__name__,
                      NumpyArrayEncDec.decode_numpy_array)
        self.register(tuple, _encode_tuple, tuple.__name__, _decode_tuple)
        for numpy_integer_type in [np.int16, np.int32, np.int64, np.float16, np.float32, np.float64, np.bool_]:
            self.register(numpy_integer_type, _encode_numpy_number, '__npnumber__', _decode_numpy_number)

    def register(self, type_: type, encode_func: TransformFunction, type_name: str,
                 decode_func: TransformFunction) -> None:
        """ Registers an encoder and decoder for a given type

        An encode function is expected to return a JSON valid type or a dictionary with the keys
        `JsonSerializeKey.OBJECT` (the name of the type) and `JsonSerializeKey.CONTENT` (the JSON valid encoded content)

        Args:
            type_: The type to encode
            encode_func: The transform function for encoding that type
            type_name: The type name to decode
            decode_func: The transform function for decoding
        """

        self.encoder.encoders[type_] = encode_func
        self.decoder.decoders[type_name] = decode_func

    def register_dataclass(self, type_: type) -> None:
        """ Registers an encoder and decoder for a dataclass with a given type

        Args:
            type_: The dataclass type to decode
        """

        type_name = f'_dataclass_{type_.__name__}'
        encode_function = partial(_encode_dataclass, class_name=type_name)
        decode_function = partial(_decode_dataclass, class_type=type_)
        self.register(type_, encode_function, type_name, decode_function)

    def serialize(self, data: Any) -> str:
        """ Serializes a Python object to JSON

        Args:
            data: Any Python object

        Returns:
            JSON encoded string
        """

        return self.encoder.encode(self.encode_data(data))

    def unserialize(self, data: str) -> Any:
        """ Unserializes a JSON string to a Python object

        Args:
            data: The JSON encoded string

        Returns:
            A Python object decoded from the JSON string
        """

        return self.decoder.decode(data)

    def encode_data(self, data: Any) -> Any:
        """ Recursively transform a Python object and apply transform functions to it

        Args:
            data: Any Python object that can be handled by an encode/transform function for that type

        Returns:
            The transformed data
        """

        if isinstance(data, dict):
            new_dict = {}

            for key, value in data.items():
                new_dict[key] = self.encode_data(value)

            return new_dict

        elif isinstance(data, list):
            new_list = []
            for item in data:
                new_list.append(self.encode_data(self._encode(item)))

            return new_list

        return self._encode(data)

    def _encode(self, data: Any) -> Any:
        type_ = type(data)
        if type_ in self.encoder.encoders:
            return self.encoder.encoders[type_](data)

        return data

    def decode_data(self, data: Any) -> Any:
        """ Recursively transform an object and apply transform functions to it

        Args:
            data: Any Python object that can be handled by an decode/transform function for that type

        Returns:
            The transformed data
        """

        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                new_dict[key] = self.decode_data(value)

            return self._decode(new_dict)

        if isinstance(data, list):
            new_list = []
            for item in data:
                new_list.append(self.decode_data(item))
            return new_list

        return data

    def _decode(self, data: Any) -> Any:
        if isinstance(data, dict):
            if JsonSerializeKey.OBJECT in data:
                if data[JsonSerializeKey.OBJECT] in self.decoder.decoders:
                    return self.decoder.decoders[data[JsonSerializeKey.OBJECT]](data)
                else:
                    raise ValueError(f'object key {data[JsonSerializeKey.OBJECT]} not in decoders')

        return data


def serialize(data: Any) -> bytes:
    """ Serializes a Python object to JSON using the default serializer. Dictionary keys should be hashable.

    Args:
        data: Any Python object
    Returns:
        JSON encoded string
    """

    return serializer.serialize(data).encode('utf8')


def unserialize(data: bytes) -> Any:
    """ Unserializes a JSON string to a Python object using the default serializer

    Args:
        data: The JSON encoded string
    Returns:
        A Python object decoded from the JSON string
    """

    return serializer.unserialize(data.decode('utf8'))


# The default Serializer to use
serializer = Serializer()
