# Authors: Michael Huang, Andrew Chen

import keras
from keras.datasets import mnist
from keras.losses import mse, binary_crossentropy
from keras import backend as K
from keras.utils import plot_model
from keras.models import Model
from keras.layers import Lambda, Input, Dense

from sklearn.model_selection import train_test_split
import numpy as np
import matplotlib.pyplot as plt
from os import sys
import argparse
import os

class VAE:

    def __init__(self):
        self.batch_size = 64
        self.kernel_size = 4
        self.filters = 32
        self.epochs = 5
        self.lr = .0001
        self.num_channels = 3
        self.model_name = "conv_vae_latent_{}_model.h5"

    def sampling(self, args):
        """Reparameterization trick by sampling from an isotropic unit Gaussian.
        # Arguments
            args (tensor): mean and log of variance of Q(z|X)
        # Returns
            z (tensor): sampled latent vector
        """

        z_mean, z_log_var = args
        batch = K.shape(z_mean)[0]
        dim = K.int_shape(z_mean)[1]
        # by default, random_normal has mean = 0 and std = 1.0
        epsilon = K.random_normal(shape=(batch, dim))
        return z_mean + K.exp(0.5 * z_log_var) * epsilon

    def plot_results(self, models,
                     data,
                     batch_size=128,
                     model_name="vae_gym"):
        """Plots labels and MNIST digits as a function of the 2D latent vector
        # Arguments
            models (tuple): encoder and decoder models
            data (tuple): test data and label
            batch_size (int): prediction batch size
            model_name (string): which model is using this function
        """

        encoder, decoder = models
        x_test, y_test = data
        # os.makedirs(model_name, exist_ok=True)

        filename = os.path.join("vae_mean.png")
        # display a 2D plot of the digit classes in the latent space
        z_mean, _, _ = encoder.predict(x_test,
                                       batch_size=self.batch_size)
        plt.figure(figsize=(12, 10))
        plt.scatter(z_mean[:, 0], z_mean[:, 1], c=y_test)
        plt.colorbar()
        plt.xlabel("z[0]")
        plt.ylabel("z[1]")
        plt.savefig(filename)
        plt.show()

        filename = os.path.join("digits_over_latent.png")
        # display a 30x30 2D manifold of digits
        n = 30
        digit_size = 28
        figure = np.zeros((digit_size * n, digit_size * n))
        # linearly spaced coordinates corresponding to the 2D plot
        # of digit classes in the latent space
        grid_x = np.linspace(-4, 4, n)
        grid_y = np.linspace(-4, 4, n)[::-1]

        for i, yi in enumerate(grid_y):
            for j, xi in enumerate(grid_x):
                z_sample = np.array([[xi, yi]])
                x_decoded = decoder.predict(z_sample)
                digit = x_decoded[0].reshape(digit_size, digit_size)
                figure[i * digit_size: (i + 1) * digit_size,
                       j * digit_size: (j + 1) * digit_size] = digit

        plt.figure(figsize=(10, 10))
        start_range = digit_size // 2
        end_range = n * digit_size + start_range + 1
        pixel_range = np.arange(start_range, end_range, digit_size)
        sample_range_x = np.round(grid_x, 1)
        sample_range_y = np.round(grid_y, 1)
        plt.xticks(pixel_range, sample_range_x)
        plt.yticks(pixel_range, sample_range_y)
        plt.xlabel("z[0]")
        plt.ylabel("z[1]")
        plt.imshow(figure, cmap='Greys_r')
        plt.savefig(filename)
        plt.show()

    def load_data(self, npz):
        data = np.load(npz)
        files = data.files
        p = np.array(data[files[0]])
        #print(data['arr_1'][0])
        files.remove(files[0])
        for i in files:
            p = np.append(p, data[i], axis=0)
        # print(p)
        x_train, x_test, y_train, y_test = train_test_split(p, p, random_state=123456)
        # print(x_train.shape)
        image_size_x = x_train.shape[1]
        image_size_y = x_train.shape[2]
        x_train = np.reshape(x_train, [-1, image_size_x, image_size_y, self.num_channels]) # 3 is # of color channels
        x_test = np.reshape(x_test, [-1, image_size_x, image_size_y, self.num_channels])
        # x_train = x_train.astype('float32') / 255
        # x_test = x_test.astype('float32') / 255
        return (x_train, y_train), (x_test, y_test)

    def make_models(self, inputs, latent_dim=2):
        self.model_name = self.model_name.format(latent_dim)
        x1 = keras.layers.convolutional.Conv2D(self.filters, self.kernel_size, strides=2, activation='relu',padding='same')(inputs)
        x2 = keras.layers.convolutional.Conv2D(self.filters*2, self.kernel_size, strides=2, activation='relu',padding='same')(x1)
        # x3 = keras.layers.Conv2D(128, 4, 2, activation='relu')(x2)
        shape = K.int_shape(x2)

        xf = keras.layers.Flatten()(x2)
        xf = Dense(16, activation='relu')(xf)
        self.z_mean = Dense(latent_dim, name='z_mean')(xf)
        self.z_log_var = Dense(latent_dim, name='z_log_var')(xf)

        self.z = Lambda(self.sampling, output_shape=(latent_dim,), name='z')([self.z_mean, self.z_log_var]) # latent vec

        encoder = Model(inputs, [self.z_mean, self.z_log_var, self.z], name='encoder')
        encoder.summary()
        # plot_model(encoder, to_file='vae_mlp_encoder.png', show_shapes=True)

        latent_inputs = Input(shape=(latent_dim,), name='z_sampling')
        y = Dense(shape[1] * shape[2] * shape[3], activation='relu')(latent_inputs)
        y = keras.layers.Reshape((shape[1], shape[2], shape[3]))(y)
        y1 = keras.layers.Conv2DTranspose(self.filters*2, self.kernel_size, strides=2, activation='relu',padding='same')(y)
        y2 = keras.layers.Conv2DTranspose(self.filters, self.kernel_size, strides=2, activation='relu',padding='same')(y1)
        # outputs = Dense(original_dim, activation='sigmoid')(y2)
        outputs = keras.layers.Conv2DTranspose(self.num_channels, self.kernel_size, strides=1, activation='sigmoid', padding='same')(y2)

        decoder = Model(latent_inputs, outputs, name='decoder')
        decoder.summary()
        # plot_model(decoder, to_file='vae_mlp_decoder.png', show_shapes=True)

        self.outputs = decoder(encoder(inputs)[2])
        vae = Model(inputs, self.outputs, name='vae_mlp')

        return encoder, decoder, self.outputs, vae

    def make_vae(self, npz, latent_size):
        (self.x_train, y_train), (self.x_test, y_test) = self.load_data(npz)
        image_size_x = self.x_train.shape[1]
        image_size_y = self.x_train.shape[2]
        input_shape = (image_size_x, image_size_y, self.num_channels)
        self.inputs = Input(shape=input_shape, name='encoder_input')
        self.encoder, self.decoder, self.outputs, self.vae = self.make_models(self.inputs, latent_size)

        # CODE THAT TESTS IF ENCODING AND DECODING WORKS
        # x_test_feed = np.reshape(self.x_test, [-1, image_size_x, image_size_y, 1])
        # latent_vector = self.encode_image(x_test_feed)
        # print("output for encode:" )
        # print(latent_vector)
        # print("output for decode:" )
        # print(self.decode_latent(latent_vector))


        models = (self.encoder, self.decoder)
        reconstruction_loss = binary_crossentropy(K.flatten(self.inputs),
                                                  K.flatten(self.outputs))
        reconstruction_loss *= image_size_x * image_size_y * self.num_channels
        kl_loss = 1 + self.z_log_var - K.square(self.z_mean) - K.exp(self.z_log_var)
        kl_loss = K.sum(kl_loss, axis=-1)
        kl_loss *= -0.5
        vae_loss = K.mean(reconstruction_loss + kl_loss)
        self.vae.add_loss(vae_loss)
        rmsprop = keras.optimizers.RMSprop(lr=self.lr, rho=0.9, epsilon=None, decay=0.0)
        self.vae.compile(rmsprop)
        self.vae.summary()

    def make_vae_shape(self, image_size_x, image_size_y, latent_size):
        input_shape = (image_size_x, image_size_y, self.num_channels)
        self.inputs = Input(shape=input_shape, name='encoder_input')
        self.encoder, self.decoder, self.outputs, self.vae = self.make_models(self.inputs, latent_size)

        # CODE THAT TESTS IF ENCODING AND DECODING WORKS
        # x_test_feed = np.reshape(self.x_test, [-1, image_size_x, image_size_y, 1])
        # latent_vector = self.encode_image(x_test_feed)
        # print("output for encode:" )
        # print(latent_vector)
        # print("output for decode:" )
        # print(self.decode_latent(latent_vector))


        models = (self.encoder, self.decoder)
        reconstruction_loss = binary_crossentropy(K.flatten(self.inputs),
                                                  K.flatten(self.outputs))
        reconstruction_loss *= image_size_x * image_size_y * self.num_channels
        kl_loss = 1 + self.z_log_var - K.square(self.z_mean) - K.exp(self.z_log_var)
        kl_loss = K.sum(kl_loss, axis=-1)
        kl_loss *= -0.5
        vae_loss = K.mean(reconstruction_loss + kl_loss)
        self.vae.add_loss(vae_loss)
        rmsprop = keras.optimizers.RMSprop(lr=self.lr, rho=0.9, epsilon=None, decay=0.0)
        self.vae.compile(rmsprop)
        self.vae.summary()

    def train_vae(self):
        self.vae.fit(self.x_train,
                epochs=self.epochs,
                batch_size=self.batch_size,
                validation_data=(self.x_test, None))
        self.vae.save_weights(self.model_name)
        # self.vae.save(self.model_name)

    def load_model(self, weights_file_path):
        self.vae.load_weights(weights_file_path)
        # self.vae = keras.models.load_model(weights_file_path)

    def encode_image(self, image):
        z_mean, z_log_var, z = self.encoder.predict(image, batch_size=32) # batch_size is can be changed depending on how much CPU/GPU RAM we have
        return z_mean

    def decode_latent(self, latent_vector):
        return self.decoder.predict(latent_vector)


    # if __name__ == '__main__':
    #     if len(sys.argv) >= 1:
    #         cmd = sys.argv[1]
    #         models = (encoder, decoder)
    #         data = (x_test, y_test)
    #         reconstruction_loss = binary_crossentropy(K.flatten(inputs), K.flatten(outputs))
    #         reconstruction_loss *= original_dim
    #         kl_loss = 1 + z_log_var - K.square(z_mean) - K.exp(z_log_var)
    #         kl_loss = K.sum(kl_loss, axis=-1)
    #         kl_loss *= -0.5
    #         vae_loss = K.mean(reconstruction_loss + kl_loss)
    #         vae.add_loss(vae_loss)
    #         vae.compile(optimizer='adam')
    #         vae.summary()
    #         # plot_model(vae,
    #         #    to_file='vae_mlp.png',
    #         #    show_shapes=True)
    #         if cmd == "train":
    #             vae.fit(x_train,
    #                 epochs=epochs,
    #                 batch_size=batch_size,
    #                 validation_data=(x_test, None))
    #             vae.save_weights('vae_mlp_mnist.h5')
    #         elif cmd == "test":
    #             vae.load_weights(args.weights)
    #         else:
    #             # print("Usage: python main-p2p.py [train, test, (optional) img output size]")
    #             print("err")
    #         plot_results(models,
    #                  data,
    #                  batch_size=batch_size,
    #                  model_name="vae_mlp")
    #     else:
    #         print("err")



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    help_ = "Load training data"
    parser.add_argument("-d", "--data", help=help_)
    help_ = "Load h5 model trained weights"
    parser.add_argument("-w", "--weights", help=help_)
    help_ = "Use mse loss instead of binary cross entropy (default)"
    parser.add_argument("-m", "--mse", help=help_, action='store_true')
    # parser.add_argument("-l", "--latent_size", help=help_)
    args = parser.parse_args()
    # latent_dim = args.latent_size
    convVae = VAE()
    convVae.make_vae(args.data, 2)
    # The below line requires a ton of arguments
    # plot_model(convVae, to_file='vae_cnn.png', show_shapes=True)

    if args.weights:
        convVae.load_model(args.weights)
    else:
        convVae.train_vae()

    # plot_results(models, data, batch_size=self.batch_size, model_name="vae_cnn")

"""
scipy.misc.imsave("del.png", convVae.decode_latent(convVae.encode_image(convVae.x_test[0:1]))[0])
columns = 2
rows = 3
fig=plt.figure(figsize=(8, 8))
t=1
for i in range(1, columns*rows +1):
    if (i % 2 == 1):
        img = convVae.x_test[t-1:t]
        t += 1
    else:
        img = convVae.decode_latent(convVae.encode_image(img))
    fig.add_subplot(rows, columns, i)
    plt.imshow(img[0])
plt.show()
"""
